import re
import subprocess

# Tools related to SNAP operators

def operator_source_flags(operator: str):
    """
    Get operator source flag from the GPT CLI. This can vary from operator
    from operator so this just extracts it from the command line output.

    Parameters
    ----------
    operator: str
        SNAP Operator as identified in the SNAP Graphs
    """
    output = subprocess.run(["gpt", operator, "-h"], capture_output=True)
    stdout = output.stdout.decode('utf-8')
    if "Unknown operator" in stdout:
        raise ValueError(stdout)
    # pattern = r"<(source)>\${source}|<(sourceProduct)>\${sourceProduct}"
    pattern = r"\${(source)}|\${(sourceProduct)}"
    match = re.search(pattern, stdout)

    if match.group(1) is None and match.group(2) is None:
        raise ValueError(f"No source flag match found for operator {operator}")
    elif match:
        if match.group(1) is not None:
            return match.group(1)
        else:
            return match.group(2)
    else:
        raise ValueError(f"No source flag match found for operator {operator}")

def get_output_suffix(action: dict) -> str:
    """
    Function imitates the default string that is usually appended to output filenames
    after using an operator as seen in SNAP.

    Parameters
    ----------
    action: dict
        Dictionary containing parameters, sources, and operator name.
    """
    operator = action.get("operator")
    parameters = action.get("parameters")
    if operator == "TOPSAR-Split":
        if not parameters.get("subswath"):
            raise ValueError("TOPSAR-Split needs a subswath parameter")
        return parameters.get("subswath")
    elif operator == "BandSelect":
        if not parameters.get("sourceBands"):
            raise ValueError("BandSelect needs a sourceBands parameter")
        return parameters.get("sourceBands")

    suffix_dict = {
        "TOPSAR-Split": None,
        "BandSelect": None,
        "SnaphuExport": "",
        "SnaphuUnwrapping": "",  # custom operator
        "Apply-Orbit-File": "Orb",
        "Back-Geocoding": "Stack",
        "Interferogram": "Ifg",
        "TOPSAR-Deburst": "Deb",
        "TopoPhaseRemoval": "Topo",
        "Coherence": "Coh",
        "Multilook": "ML",
        "GoldsteinPhaseFiltering": "Flt",
        "Subset": "Subset",
        "Terrain-Correction": "TC",
        "SnaphuImport": "Unw",
        "Import-Vector": "Vec",
        "Land-Sea-Mask": "Msk"
    }

    out = suffix_dict.get(operator)
    if out is None:
        raise ValueError(f"Operator '{operator}' not recognized as a valid SNAP Graph operator")
    return out

if __name__ == "__main__":
    pass
