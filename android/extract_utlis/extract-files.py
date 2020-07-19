from extract_utlis import ExtractUtils

# Initialize the class
extract = ExtractUtils()

extract.setup_vendor("PL2", "nokia", "/home/aayush/github")
extract.extract_files("/home/aayush/proprietary-files.txt")
