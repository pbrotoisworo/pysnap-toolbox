from datetime import datetime
import os
import shutil
import xml.etree.ElementTree as ET
from zipfile import ZipFile

def get_datetime(platform: str, path: str):

    if path.endswith('.dim'):
    
        tree = ET.parse(path)
        root = tree.getroot()
        datetime_str = root.find(".//PRODUCT_SCENE_RASTER_START_TIME")
        if datetime_str is None:
            raise LookupError(f"Cannot find datetime from BEAM-DIMAP file {path}")
        
        if "T" in datetime_str.text:
            dt_obj = datetime.strptime(datetime_str.text, r"%Y-%m-%dT%H:%M:%S.%f")
        else:
            dt_obj = datetime.strptime(datetime_str.text, r"%d-%b-%Y %H:%M:%S.%f")

    else:
        if platform == "SENTINEL-1":
            # Extract manifest.safe file
            with ZipFile(path) as f:
                manifest = None
                for item in f.filelist:
                    if "manifest.safe" in item.filename:
                        manifest = item.filename
                f.extract(manifest, "")
            
            # Parse XML
            tree = ET.parse(manifest)
            metadata = tree.getroot()
            datetime_str = metadata.find((".//safe:startTime"), {'safe': r"http://www.esa.int/safe/sentinel-1.0"})
            if datetime_str is None:
                raise LookupError("cannot find scene start time in Sentinel-1 .SAFE file")
            dt_obj = datetime.strptime(datetime_str.text, r"%Y-%m-%dT%H:%M:%S.%f")
            
            # Clean up
            shutil.rmtree(os.path.dirname(manifest))
        else:
            raise ValueError(f"Unsupported sensor: {platform}")
    return dt_obj
