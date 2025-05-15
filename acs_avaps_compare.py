# acs_avaps_compare.py

import argparse
import os
import glob
import re
from netCDF4 import Dataset
import numpy.ma as ma
from datetime import datetime, timedelta


def extract_launch_time(filename):
    # Matches pattern like AR2025-20250223N1-01-20250223T203707-5.nc
    match = re.search(r'(\d{8})T(\d{6})', filename)
    if match:
        date, time = match.groups()
        return f"{date}_{time}"
    return "UNKNOWN"


def adjust_launch_time(launch_time):
    # Adjust the launch time by one second
    try:
        dt = datetime.strptime(launch_time, "%Y%m%d_%H%M%S")
        adjusted_dt = dt + timedelta(seconds=1)
        return adjusted_dt.strftime("%Y%m%d_%H%M%S")
    except ValueError:
        return launch_time


def find_d_file(directory, launch_time):
    # Look for file like D20250223_203707.* in the directory
    pattern = os.path.join(directory, f"D{launch_time}.*")
    matches = glob.glob(pattern)
    if matches:
        return matches[0]
    # Try adjusting the launch time by 1 second and search again
    adjusted_launch_time = adjust_launch_time(launch_time)
    pattern = os.path.join(directory, f"D{adjusted_launch_time}.*")
    matches = glob.glob(pattern)
    return matches[0] if matches else None


def compare_data(netcdf_file, d_file, launch_time):
    # Placeholder for comparison logic between NetCDF and D files
    print(f"Comparing {netcdf_file} with {d_file}")
    # open .nd file
    dataset = Dataset(netcdf_file, 'r')
    #gpsutctime: milliseconds since 1970-01-01 23:40:14 +0000 UTC
    #sampletime: milliseconds since 2025-02-20 23:39:35.207027 +0000 UTC
    gpsutctime_start_str=dataset.groups['Profile'].variables['GpsUtcTime'].units
    sampletime_start_str=dataset.groups['Profile'].variables['SampleTime'].units
    #create a datetime object, but use the date value from sampletime with the time from gpsutctime
    #can be an issue of the two are started crossing the midnight boundary
    timestamp_str = sampletime_start_str.split()[2] + 'T' + gpsutctime_start_str.split()[3] + '+0000'
    try:
        gpsutctime_start = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%f%z")
    except ValueError:
        gpsutctime_start = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S%z")
    acs_launchdetect=dataset.getncattr('DropLaunchDetect')
    #for att in dataset.ncattrs():
    #    print(att+': '+str(dataset.getncattr(att)))

    acs_sounding={}
    #loop through every time value
    for i in range(dataset.groups['Profile'].variables['GpsUtcTime'].shape[0]):
        #dont add if GpsUtcTime is not available
        if dataset.groups['Profile'].variables['GpsUtcTime'][i] is not ma.masked:
            sample={}
            millisec_delta=int(dataset.groups['Profile'].variables['GpsUtcTime'][i])
            timetag=gpsutctime_start+timedelta(milliseconds=millisec_delta)
            timetag_str=timetag.strftime("%Y-%m-%dT%H:%M:%S.%f")[0:-4]+"Z"
            
            for v in dataset.groups['Profile'].variables:
                if dataset.groups['Profile'].variables[v][i] is not ma.masked:
                    sample[v]=float(dataset.groups['Profile'].variables[v][i])
                else:
                    sample[v]=None
            acs_sounding[timetag_str]=sample
    

    file_name = d_file
    avaps_sounding={}
    with open(file_name, 'r') as file:
        for line in file:
            #not a data line
            if line.startswith('AVAPS-T'):
                #not an end of drop paramater line
                if line.count(':') > 0:
                    label,value=line.split(":",1)
                    if label.count('Launch Time') > 0:
                        avaps_launchdetect=value.strip().replace(", ","T")+"Z"
                        #print(value)
                    elif label.count('Sonde ID') > 0:
                        value=int(value.strip().split(",")[0])
                        #print(value)

            #data line
            elif line.startswith('AVAPS-D'):
                sample={}
                vals=line.split()
                
                #vals[0] is AVAPS-D01
                #vals[1] is Pxx LAU Axx
                #skip over the A00 or LAU lines
                if vals[1][0] not in ["S", "P"]:
                    continue

                
                #vals[2] is Sonde ID
                sample["ID"]=int(vals[2])
                
                #vals[3] is YYMMDD
                #vals[4] is HHMMSS.SS
                utc="20"+vals[3][0:2]+"-"+vals[3][2:4]+"-"+vals[3][4:6]+"T"+vals[4][0:2]+":"+vals[4][2:4]+":"+vals[4][4:9]+"Z"

                #vals[5] is Pressure
                if vals[5] == "9999.00":
                    sample["Pressure"] = None
                else:
                    sample["Pressure"] = float(vals[5])

                #vals[6] is Temperature
                if vals[6] == "99.00":
                    sample["Temperature"] = None
                else:
                    sample["Temperature"] = float(vals[6])

                #vals[7] is Humidity
                if vals[7] == "999.00":
                    sample["Humidity"] = None
                else:
                    sample["Humidity"] = float(vals[7])

                #vals[8] is Wind Direction
                if vals[8] == "999.00":
                    sample["WindDirection"] = None
                else:
                    sample["WindDirection"] = float(vals[8])

                #vals[9] is Wind Speed
                if vals[9] == "999.00":
                    sample["WindSpeed"] = None
                else:
                    sample["WindSpeed"] = float(vals[9])

                #vals[10] is Vertical Velocity (assume GPS?)
                if vals[10] == "99.00":
                    sample["GpsDzDt"] = None
                else:
                    sample["GpsDzDt"] = float(vals[10])

                #vals[11] is Longitude
                if vals[11] == "999.000000":
                    sample["Longitude"] = None
                else:
                    sample["Longitude"] = float(vals[11])

                #vals[12] is Latitude
                if vals[12] == "99.000000":
                    sample["Latitude"] = None
                else:
                    sample["Latitude"] = float(vals[12])

                #vals[13] is GeoPotential Altitude
                if vals[13] == "99999.00":
                    sample["GeoAltitude"] = None
                else:
                    sample["GeoAltitude"] = float(vals[13])

                #vals[14] is GPS Wind Sat
                sample["GpsSats"] = int(vals[14])

                #vals[15] is RH1 
                #(unsure how this differes from Humidity Above
                if vals[15] == "999.00":
                    sample["RH1"] = None
                else:
                    sample["RH1"] = float(vals[15])

                #vals[16] is RH2
                #appears to always be 999.00
                if vals[16] == "999.00":
                    sample["RH2"] = None
                else:
                    sample["RH2"] = float(vals[16])

                #vals[16] is GPS Snd Sat
                sample["GpsSndSat"] = int(vals[17])
                
                if vals[18] == "99.00":
                    sample["wind_err"] = None
                else:
                    sample["wind_err"] = float(vals[18])

                if vals[19] == "99999.00":
                    sample["gps_alt"] = None
                else:
                    sample["gps_alt"] = float(vals[19])
                    
                avaps_sounding[utc]=sample

    def round_digits( num, dec_digits ):
        val=num * pow(10,dec_digits)
        ival=int(val)
        return float(ival / pow(10,dec_digits))

    def write_val(f, value):
        f.write(',')
        if value is not None:
            f.write(str(value))

    def append_output(f, tt, avaps_key, acs_key, dig):
        #write the AVAPS value
        if tt in avaps_sounding and avaps_key in avaps_sounding[tt]:
            avaps_val=avaps_sounding[tt][avaps_key]
        else:
            avaps_val=None
        
        #write the ACS equivalent
        if tt in acs_sounding and acs_key in acs_sounding[tt]:
            acs_val=acs_sounding[tt][acs_key]
        else:
            acs_val=None

        #round the ACS value to the same # digits as AVAPS
        if acs_val is None:
            acs_val_rnd=None
        else:
            acs_val_rnd=round_digits(acs_sounding[tt][acs_key],dig)
        
        write_val(f, avaps_val)
        write_val(f, acs_val)
        write_val(f, acs_val_rnd)
        if ( acs_val is not None ) and (avaps_val is not None):
            write_val(f, avaps_val - acs_val_rnd)
        else:
            write_val(f, None)


    # Define subdirectory
    output_dir = "processed"

    # Make sure it exists
    os.makedirs(output_dir, exist_ok=True)

    # Use it in your file path
    csv_path = os.path.join(output_dir, f"{launch_time}.csv")

    # Open the files
    f = open(csv_path, "w")

    f.write('GPS UTC Timetag,')
    f.write('AVAPS air_press,ACS Pressure,ACS Rounded Pressure,AVAPS - ACS Pressure,'      )
    f.write('AVAPS air_temp,ACS Temperature,ACS Rounded Temperature,AVAPS - ACS Temperature,'   )
    f.write('AVAPS rel_hum,ACS Humidity,ACS Rounded Humidity,AVAPS - ACS Humidity,'      )
    f.write('AVAPS wind_dir,ACS WindDirection,ACS Rounded WindDirection,AVAPS - ACS WindDirection,' )
    f.write('AVAPS wind_spd,ACS WindSpeed,ACS Rounded WindSpeed,AVAPS - ACS WindSpeed,'     )
    #f.write('AVAPS vert_vel,ACS GpsDzDt,ACS Rounded GpsDzDt,AVAPS - ACS GpsDzDt,'       )
    #f.write('AVAPS vert_vel,ACS PDzDt,ACS Rounded PDzDt,AVAPS - ACS PDzDt,'         )
    #f.write('AVAPS gps_long,ACS Longitude,ACS Rounded Longitude,AVAPS - ACS Longitude,'     )
    #f.write('AVAPS gps_lat,ACS Latitude,ACS Rounded Latitude,AVAPS - ACS Latitude,'      )
    #f.write('AVAPS geop_alt,ACS GeoAltitude,ACS Rounded GeoAltitude,AVAPS - ACS GeoAltitude,'   )
    #f.write('AVAPS gps_wnd_sat,ACS GpsSats,ACS Rounded GpsSats,AVAPS - ACS GpsSats,'       )
    #f.write('AVAPS rh1,ACS SensorHumidity,ACS Rounded SensorHumidity,AVAPS - ACS SensorHumidity,')
    #f.write('AVAPS wind_err,ACS GpsSpeedAcc,ACS Rounded GpsSpeedAcc,AVAPS - ACS GpsSpeedAcc,'   )
    #f.write('AVAPS gps_alt,ACS GpsAltitude,ACS Rounded GpsAltitude,AVAPS - ACS GpsAltitude,'   )
    #f.write('\n')

    #get the first and last timetag of each sounding, 
    #then get the minimum between the two where they both were recording
    if not acs_sounding or not avaps_sounding:
        print(f"Warning: Missing data for {launch_time}.")
        print(f"  ACS points: {len(acs_sounding)}")
        print(f"  AVAPS points: {len(avaps_sounding)}")
        return

    acs_first_tt=sorted(acs_sounding.keys())[0]
    acs_last_tt=sorted(acs_sounding.keys())[len(acs_sounding)-1]
    acs_first_tt=sorted(acs_sounding.keys())[0]
    acs_last_tt=sorted(acs_sounding.keys())[len(acs_sounding)-1]
    avaps_first_tt=sorted(avaps_sounding.keys())[0]
    avaps_last_tt=sorted(avaps_sounding.keys())[len(avaps_sounding)-1]
    if avaps_first_tt > acs_first_tt:
        both_first_tt=avaps_first_tt
    else:
        both_first_tt=acs_first_tt
    if avaps_last_tt < acs_last_tt:
        both_last_tt=avaps_last_tt
    else:
        both_last_tt=acs_last_tt    

    #get all timetags from both sounding to get a full list
    all_tt=list(acs_sounding.keys())
    for tt in avaps_sounding.keys():
        if not tt in all_tt:
            all_tt.append(tt)
            #print('add: '+tt)
    all_tt.sort()

    #ff = open(f"{launch_time}.txt", "w")
    for tt in all_tt:
        #ff.write(tt+'   ')
        #if tt in avaps_sounding:
        #    if 'geop_alt' in avaps_sounding[tt]:
        #        ff.write('AVAPS {:10s} '.format(str(avaps_sounding[tt]['geop_alt'])))
        #    else:
        #        ff.write('AVAPS {:10s} '.format('N/A'))  # or some default/fallback value
        #else:
        #    ff.write('                ')
        #if tt in acs_sounding:
        #    ff.write('ACS: {:10s}'.format(str(acs_sounding[tt]['GeoAltitude'])))
        #else:
        #    ff.write('               ')
        #ff.write('\n')

        f.write(tt)
        append_output(f, tt, 'Pressure',    'Pressure',       2)
        append_output(f, tt, 'Temperature',     'Temperature',    2)
        append_output(f, tt, 'Humidity',      'Humidity',       2)
        append_output(f, tt, 'WindDirection',     'WindDirection',  2)
        append_output(f, tt, 'WindSpeed',     'WindSpeed',      2)
        #append_output(f, 'vert_vel',     'GpsDzDt',        2)
        #append_output(f, 'vert_vel',     'PDzDt',          2)
        #append_output(f, 'gps_lon',      'Longitude',      6)
        #append_output(f, 'gps_lat',      'Latitude',       6)
        #append_output(f, 'geop_alt',     'GeoAltitude',    2)
        #append_output(f, 'gps_wnd_sat',  'GpsSats',        0)
        #append_output(f, 'rh1',          'SensorHumidity', 2)
        #append_output(f, 'wind_err',     'GpsSpeedAcc',    2)
        #append_output(f, 'gps_alt',      'GpsAltitude',    2)
        f.write('\n')










def main():
    parser = argparse.ArgumentParser(description="Compare ACS and AVAPS dropsonde data in a given directory.")
    parser.add_argument("directory", type=str, help="Path to the directory containing data files")
    args = parser.parse_args()

    directory = args.directory
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory.")
        return

    # Find all NetCDF files in the directory
    netcdf_files = glob.glob(os.path.join(directory, "*.nc"))
    print(f"Found {len(netcdf_files)} NetCDF files:")
    for file in netcdf_files:
        launch_time = extract_launch_time(os.path.basename(file))
        d_file = find_d_file(directory, launch_time)
        print(f"  {file} -> Launch time: {launch_time} -> D file: {d_file if d_file else 'NOT FOUND'}")

        if d_file:
            compare_data(file, d_file, launch_time)

    # Placeholder for data loading and comparison logic

if __name__ == "__main__":
    main()