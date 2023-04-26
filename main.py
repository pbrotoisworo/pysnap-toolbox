import argparse
from pysnaptoolbox.config import Runner, TomlConfig

def main(**kwargs):
    Runner(**kwargs)

if __name__ == "__main__":


    # Get arguments. It will be split into defined main args and custom user args
    # parser = argparse.ArgumentParser(description='pysnap-toolbox command line interface')

    # main_args = parser.add_argument_group('Required Parameters')
    # main_args.add_argument('--template-dir', help='Path containing template files', default='templates')
    # main_args.add_argument('--template', help='Basename of template file (filename only)')
    # main_args.add_argument('--workflow', help='Type of workflow')
    # main_args.add_argument('--images', help='Images to be used for the workflow', nargs='+', type=str)

    main_parser = argparse.ArgumentParser(description='pysnap-toolbox command line interface')
    main_args_group = main_parser.add_argument_group('Required Parameters')
    main_args_group.add_argument("--workflow", help='Type of workflow')
    main_args_group.add_argument("--platform", help="Satellite platform used to capture data")
    main_args_group.add_argument("--output-dir", help="Path of output directory")
    # main_args_group.add_argument('--images', help='Type of workflow', nargs='+', type=str)
    
    # batch_args = main_parser.add_argument_group("Batch Processing")
    # batch_args.add_argument('--batch', help='Input directory containing image data used as input for batch image processing.')

    # Check for user arg input
    # main_args, user_args_raw = main_parser.parse_known_args()
    # if len(user_args_raw) == 0:
    #     raise NoUserArgumentsException("No user arguments detected.")
    # Get main kwargs (defined script args)
    # main_args = vars(main_args)

    # # Parse user args
    # user_args = {}
    # for arg in user_args_raw:
    #     if arg.startswith(("-", "--")):
    #         arg_split = arg.split("=")
    #         key = arg_split[0].lstrip("-").lstrip("--")
    #         user_args[key] = arg_split[1]

    args = vars(main_parser.parse_args())
    config = TomlConfig()
    config.load_config(args["workflow"])
    output = Runner(config, args["platform"], args["output_dir"])
    output.run_config()
