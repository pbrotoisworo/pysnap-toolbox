import os
import subprocess

import toml

from .operators import get_output_suffix, operator_source_flags
from .dates import get_datetime

class TomlConfig(dict):
    def __init__(self, *args, **kwargs):
        """
        Parse the TOML config and converts it into a dictionary object.
        There are additional methods and attributes that can be used to
        quickly access relevant parameters.
        """
        super(TomlConfig, self).__init__(*args, **kwargs)
        self.input_sources = None
        self.sub_workflow_names = []
        self.sub_workflow_data = {}

    def load_config(self, path):
        """
        Load the TOML config file and re-initialize the TomlConfig object with
        the data from the TOML config file.
        """
        with open(path) as f:
            lines = f.readlines()
        
        # Iterate through lines and find ones with reserved escape sequences
        # If exists, add an extra backslash to escape it
        for i, line in enumerate(lines):
            escaped_string = ""
            if "\\" in line:
                for char in line:
                    if char == "\\":
                        escaped_string += "\\\\"
                    else:
                        escaped_string += char
                lines[i] = escaped_string
        
        # Reload class with TOML data
        self.__init__(toml.loads("\n".join(lines)))
        
        if "sources" in self.keys():
            self.sources = self["sources"]
        
        self.sub_workflow_names = list(self["workflow"].keys())
        self.sub_workflow_data = self["workflow"]

    def __setitem__(self, key, value):
        super(TomlConfig, self).__setitem__(key, value)

    def __getitem__(self, key):
        return super(TomlConfig, self).__getitem__(key)

    def __delitem__(self, key):
        super(TomlConfig, self).__delitem__(key)

    def __repr__(self):
        return super(TomlConfig, self).__repr__()

    def __len__(self):
        return super(TomlConfig, self).__len__()

    def __iter__(self):
        return super(TomlConfig, self).__iter__()

    def __contains__(self, item):
        return super(TomlConfig, self).__contains__(item)


class Runner:

    def __init__(self, config: TomlConfig, platform: str, output_dir: str, debug_mode: bool = False) -> None:
        """
        Takes in a TomlConfig object and allows the user to run
        SNAP processing methods.
        """
        self.config = config
        self.platform = platform.upper()
        self.output_dir = output_dir
        self.debug_mode = debug_mode

        # Initialize namespace
        self.namespace = self.config["sources"]

    # def _get_multiple_source_file_arg(self, op: str, sources):
    #     flag = "Ssource"
    #     output = ""
    #     for i, source in enumerate(sources.split(","), 1):
    #         output += f'{flag}{i}="{source}" '
    #     return output

    def generate_cli_command(self, op: str, sources: str, target: str, param: dict):
        
        if op in ["Back-Geocoding"]:
            # The sources will be the first arguments without any flag such as:
            # gpt Back-Geocoding img1.dim img2.dim param1=foo param2=bar
            cmd = f'gpt {op} '
            for file in sources.split(","):
                cmd += file + " "
        else:
            source_flag = operator_source_flags(op)
            cmd = f'gpt {op} -S{source_flag}="{sources}"'
        cmd = cmd.replace("  ", " ")
        # Add parameters if they exist
        if param:
            for param_name, value in param.items():
                if str(value).isnumeric():
                    cmd += f' -P{param_name}={value}'
                else:
                    cmd += f' -P{param_name}="{value}"'

        # Add output
        cmd += f' -t "{target}"'

        return cmd
    
    def get_source_files(self, sources, section: str):
        print("DEBUG NAMESPACE", self.namespace)

        # We are expecting an array from sources
        source_string = ""
        if isinstance(sources, str):
            sources = [sources]
        for source in sources:
            # If the source has a $ sign at the beginning
            # remove $ sign and extract from namespace
            if source.startswith("$"):
                source = source.lstrip("$")
                source = self.namespace[source]
            source_string += f"{source},"
        source_string = source_string.rstrip(",")
        return source_string
    
    def run_config(self):

        target_file = ""
        datetimes = []
        for section in self.config.sub_workflow_data:
            print("\nDEBUG: Starting new section")
            for i, action in enumerate(self.config["workflow"][section]):

                # Handle path namespace logic here then feed it into generate_cli_command
                if action.get("source") is None and section not in self.namespace.keys():
                    raise RuntimeError("No source is specified but existing path not found in namespace or config file")
                elif action.get("source") is None and i == 0:
                    raise RuntimeError(f"No source was specified for section {section} operator {action.get('operator')}")
                elif action.get("source") is None:
                    source = self.namespace[section]
                else:
                    print("BLEH2", action.get("source"))
                    source = self.get_source_files(action.get("source"), section)

                # If the target file is empty, create new file basename from datetime
                # If one date then do something like 20220623
                # If two dates then do something lime 20220623_20220701
                if i == 0:
                    for file in source.split(","):
                        dt_obj = get_datetime(self.platform, file)
                        target_file += dt_obj.strftime(r"%Y%m%d") #+ "_"
                    target_file = os.path.join(self.output_dir, target_file) + ".dim"

                # Append operator suffix to output filename
                # suffix = get_output_suffix(action)
                suffix = action.get("outputBasename")
                target_file = target_file.replace(".dim", f"_{suffix}.dim")
                # print("DEBUG3:", target_file)

                cmd = self.generate_cli_command(action.get("operator"), source, target_file, action.get("parameters"))
                print("DEBUG CMD", cmd)
                # Run CLI command using subprocess
                subprocess.call(cmd, shell=True)

                # Update path namespace after every action
                self.namespace[section] = target_file

            target_file = ""

            
        return


if __name__ == "__main__":
    pass
