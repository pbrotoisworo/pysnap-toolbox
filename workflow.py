import argparse
from copy import deepcopy
from datetime import datetime
from glob import glob
import os
import shutil
import subprocess
import toml
from typing import Union
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from operators import default_operator_suffix, operator_source_flags
from snaphu import run_snaphu


class WorkflowGroup:

    def __init__(self) -> None:
        """
        Object to store workflow sub-table properties in the TOML config file.
        """
        self.source = None
        self.processing_steps = []
        self.latest_dim_path = None
        self.datetimes = []

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

def run_processing_groups(group: WorkflowGroup, output_dir: str, platform: str):

    group_output_paths = {}
    latest_dim_file = None
    source_arg = None
    target_file = None
    snaphu_phase_file = None
    snaphu_unwrap_phase_file = None
    snaphu_target_dir = None
    kwargs = {}

    # Loop through processing_group
    for group_name, group_data in group.items():
        # Loop through steps in group
        for i, process_group in enumerate(group_data.processing_steps):

            operator = process_group["operator"]

            #########################
            # Handle input file logic
            #########################
            # Check for error situation
            if not process_group.get("source") and i == 0:
                raise RuntimeError("source is required for the first item in a processing group")
            
            source_arg = ""
            source_count = 1
            flag = "-" + operator_source_flags(operator)

            # We are expecting an array of sources to make things easier
            if isinstance(group_data.source, str):
                group_data.source = [group_data.source]

            # TODO: Special cases (separate funcs?) for operators instead of a bunch of nested statements

            # Iterate through it and add to cmd string
            if i > 0:
                source = latest_dim_file
                source_arg += f'{flag}="{source}" '
                source_count +=1
            else:
                for source in group_data.source:
                    # Load latest output path from specified processing group
                    if source.startswith("$"):
                        source = group_output_paths[source.lstrip("$")]
                    if len(group_data.source) > 1:
                        source_arg += f'{flag}{source_count}="{source}" '
                        source_count +=1
                    else:
                        source_arg += f'{flag}="{source}" '
            
            # Override if SnaphuImport (Special case)
            if operator == "SnaphuImport":
                # SnaphuExport, SnaphuUnwrapping should've been done at this point
                source_arg = f'-PwrappedPhase={snaphu_phase_file} -PunwrappedPhase={snaphu_unwrap_phase_file}'
            
            #########################
            # Handle output file logic
            #########################
            # TODO: Special cases (separate funcs?) for operators instead of a bunch of nested statements
            if operator == "TOPSAR-Split":
                kwargs["subswath"] = process_group["parameters"]["subswath"]
            suffix = default_operator_suffix(operator, **kwargs)

            for source in group_data.source:
                if source.startswith("$"):
                    source = group_output_paths[source.lstrip("$")]
                dt = get_datetime(platform, source)
                if dt is not None:
                    group_data.datetimes.append(dt)

            if i == 0:
                if operator == "Back-Geocoding":
                    # Use first and last date in the array to show range of datetime
                    first = group_data.datetimes[0]
                    last = group_data.datetimes[-1]
                    first_str = f"{first.year}{first.month}{first.day}"
                    last_str = f"{last.year}{last.month}{last.day}"
                    datetime_str = f'{first_str}_{last_str}'
                else:
                    date = group_data.datetimes[0]
                    datetime_str = f'{date.year}{date.month}{date.day}'
                target_file = os.path.join(output_dir, f'{datetime_str}.dim')

            if suffix != "":
                target_file = target_file.rstrip(".dim")
                target_file += f'_{suffix}{".dim"}'

            if operator == "SnaphuExport":
                snaphu_phase_file = target_file

            #########################
            # Handle parameter logic
            #########################
            parameters = ""
            
            if process_group.get("parameters"):
                for param, value in process_group["parameters"].items():
                    if str(value).isnumeric():
                        parameters += f'-P{param}={value} '
                    elif operator == "SnaphuExport" and param == "targetFolder":
                        snaphu_target_dir = value
                        parameters += f'-P{param}="{value}" '
                    else:
                        parameters += f'-P{param}="{value}" '

            # Create GPT command
            if operator == "SnaphuExport":
                cmd = f'gpt {operator} {parameters} {source_arg}'
            elif operator == "Subset":
                operator = os.path.join(os.path.dirname(__file__), "graphs", "subset.xml")
                cmd = f'gpt {operator} {parameters} {source_arg} -PoutputFile="{target_file}"'
            elif operator == "SnaphuImport":
                operator = os.path.join(os.path.dirname(__file__), "graphs", "snaphuImport.xml")
                cmd = f'gpt {operator} {parameters} {source_arg} -PoutputFile="{target_file}"'
            else:
                cmd = f'gpt {operator} {parameters} {source_arg} -t "{target_file}"'
            cmd = cmd.replace("  ", " ")

            print("\n#######################################")
            print("Processing group:", group_name)
            print("Running", operator, "operator")
            print("GPT command:", cmd)
            # print("DEBUG: Group sources", group_data.source)
            # print("DEBUG: Latest dim file", latest_dim_file)
            print("#######################################\n")

            # Some operators require external non GPT software
            if operator == "SnaphuUnwrapping":
                if snaphu_target_dir is None:
                    raise RuntimeError("Error with SnaphuUnwrapping operator. \
                                       Could not detect SnaphuExport targetFolder. \
                                       SnaphuExport needs to be in the same workflow.")
                run_snaphu(snaphu_target_dir, process_group["parameters"])
                snaphu_unwrap_phase_file = glob(os.path.join(snaphu_target_dir, "*", "UnwPhase*.snaphu.hdr"))[0]
                
            else:
                subprocess.call(cmd, shell=True)

            # Update latest path
            latest_dim_file = target_file
            group_output_paths[group_name] = latest_dim_file

    return latest_dim_file

def prepare_source_args(i: int, operator: str, group_data: WorkflowGroup, latest_dim_file: str):
    
    source_arg = ""
    source_count = 1

    # Check if it a single path or an array of paths
    # If list iterate through it and add to cmd string
    if isinstance(group_data.source, list):
        for source in group_data.source:
            source = source if i == 0 else latest_dim_file
            flag = "-" + operator_source_flags(operator)
            source_arg += f'{flag}{source_count}="{source}" '
            source_count +=1
    # Else if just replace cmd string
    elif isinstance(group_data.source, str):
        source = group_data.source if i == 0 else latest_dim_file
        flag = "-" + operator_source_flags(operator)
        source_arg += f'{flag}="{source}" '

    return source_arg

def parse_processing_group(group_name, group) -> WorkflowGroup:

    wg = WorkflowGroup()
    for i, item in enumerate(group):
        if i == 0:
            wg.source = item.get("source")
            if not wg.source:
                print("ERROR: Missing source in TOML config")
                print(group)
                raise KeyError(f"Missing source in TOML config for processing group workflow.{group_name}")
    return wg

def run(toml_template: Union[str, dict], platform: str, output_dir: str = "", cleanup_ignore_list: list = [], cleanup: bool = True):

    if isinstance(toml_template, str):
        with open(toml_template) as f:
            config = toml.load(f)
    elif isinstance(toml_template, dict):
        config = toml_template
    else:
        raise RuntimeError("toml template for run() function only supports dict or str inputs")    
    
    # Parse pysnaptoolbox TOML reference
    # Parse data into objects to help keep track of different processing groups
    workflow_groups = {}
    for group in config["workflow"]:
        workflow_groups[group] = parse_processing_group(group, config["workflow"][group])
        # Parse group processing steps into processing_steps property
        for process in config["workflow"][group]:
            workflow_groups[group].processing_steps.append(process)

    # Run workflow groups
    protected_output_dim = run_processing_groups(workflow_groups, output_dir, platform)
    protected_output_data = protected_output_dim.replace('.dim', '.data')

    if cleanup:
        dim_files = glob(os.path.join(output_dir, '*.dim'))
        data_dirs = glob(os.path.join(output_dir, '*.data'))
        for dim in dim_files:
            if dim != protected_output_dim and dim not in cleanup_ignore_list:
                os.remove(dim)
        for data_dir in data_dirs:
            if data_dir != protected_output_data and data_dir not in cleanup_ignore_list:
                shutil.rmtree(data_dir)
    return protected_output_dim, protected_output_data

def run_batch_processing(toml_template: str, batch_folder: str, batch_subtables: str, platform: str,
                              output_dir: str = "", batch_folder_glob: str = "*", cleanup: bool = True,
                              step: int = 1):
    """
    Run batch processing using a TOML file as a reference file. The data in input directory path `batch_folder`
    will automatically be inserted as the source for each processing item.
    """

    with open(toml_template) as f:
        config = toml.load(f)

    # Get image batches
    image_batches = []
    batch_subtables = batch_subtables.split(',')
    batch_size = len(batch_subtables)
    # Iterate through files
    for i in range(0, len(files), step):
        if i + batch_size <= len(files):
            batch = []
            # Get batch size according to the size of entry points
            for j in range(batch_size):
                try:
                    batch.append(files[i+j])
                except IndexError:
                    break
            image_batches.append(batch)
    
    workflow_list = []
    # construct workflow from batches
    for batch in image_batches:
        # Make a copy of the config file which will be appended to the workflow list
        config_copy = deepcopy(config)
        for i, image in enumerate(batch):
            config_copy["workflow"][batch_subtables[i]][0]["source"] = image
        workflow_list.append(config_copy)

    # Save a copy of full workflow to TOML file for reference
    toml_out = {}
    for i, workflow in enumerate(workflow_list):
        toml_out[str(i)] = workflow["workflow"]
    with open(os.path.join(output_dir, "workflow.toml"), "w") as f:
        toml.dump(toml_out, f)

    # Run workflows
    # print("Processing", len(workflow_list), "scene pairs")
    protected_data = []
    for workflow in workflow_list:
        output_dim, output_data = run(workflow, platform, output_dir, protected_data, cleanup=cleanup)
        # If cleanup is enabled these files will be protected from cleanup
        protected_data.append(output_dim)
        protected_data.append(output_data)

def download_s3(bucket: str, prefix:str, profile: str = "default"):
    """
    Iterate through a specified S3 bucket directory. The files will be sorted according
    to their filename.
    """
    try:
        import boto3
    except ImportError as e:
        raise ImportError("boto3 is not installed. Install boto3 in your environment to use this function.")

    # create an S3 client object
    session = boto3.Session(profile_name=profile)
    s3 = session.client('s3')
    # response = s3.list_buckets()
    # for bucket in response['Buckets']:
    #     print(f'  {bucket["Name"]}')
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    for item in response['Contents']:
        print(item['Key'])

    return

if __name__ == "__main__":

    # Define CLI flags and parse inputs
    parser = argparse.ArgumentParser(description='pysnap-toolbox command line interface')

    main_args = parser.add_argument_group('Global Parameters')
    main_args.add_argument('--pattern', help='Optional glob pattern used to filter data for batch processing')
    main_args.add_argument('--config', help='Input TOML config file for a single SNAP workflow or to be used as a template for batch processing')
    main_args.add_argument('--output-dir', help='Output directory for processed data')
    main_args.add_argument('--platform', help='Satellite platform that was used to capture the data')
    main_args.add_argument('--cleanup', action='store_true', help='Clean up scratch files after workflow is finished')
    main_args.add_argument('--aws-profile', help="Name of the aws credential profile to use", default='default')
    main_args.add_argument('--aws-bucket', help="Name of the AWS S3 bucket to access")

    batch_args = parser.add_argument_group("Batch Processing")
    batch_args.add_argument('--batch', help='Input directory containing image data used as input for batch image processing. \
                           Can be a local directory or an S3 URI link that starts with "s3://"')
    batch_args.add_argument('--batch-step', help="Number of files to skip ahead in a folder when a batch of files is done.", default=1)
    batch_args.add_argument('--batch-subtables', help='Target subtables used to identify the entry points in your TOML file. \
                    The number of entry points indicate the number of files that will be processed per batch (batch size). \
                    A subtable can be seen as [[workflow.image1]] and [[workflow.image2]]. This would be a comma separated list \
                    such as image1,image2. During pair processing the first image pair is considered the reference image. i.e., \
                    image1 is considered the reference image and image2 is secondary.')

    args = parser.parse_args()
    args = vars(args)

    if not args["batch"]:
        run(args["config"], args["platform"], args["output_dir"], [], args["cleanup"])
    else:
        if not args["pattern"]:
            args["pattern"] = "*"
        run_batch_processing(args["config"], args["batch"], args["batch_subtables"], args["platform"], args["output_dir"], args["pattern"], args["cleanup"], args["batch_step"])


