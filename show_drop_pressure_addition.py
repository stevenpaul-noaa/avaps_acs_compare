import sys
from netCDF4 import Dataset

def show_drop_pressure_addition(nc_file_path):
    try:
        with Dataset(nc_file_path, 'r') as nc:
            if "DropPressureAddition" in nc.ncattrs():
                value = nc.getncattr("DropPressureAddition")
                print(f'DropPressureAddition: {value}')
            else:
                print("Global attribute 'DropPressureAddition' not found.")
    except Exception as e:
        print(f"Error reading NetCDF file: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python show_attr.py <path_to_netcdf_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    show_drop_pressure_addition(file_path)
