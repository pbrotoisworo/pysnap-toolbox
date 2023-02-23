# What is pysnap-toolbox?
A lightweight python wrapper for [ESA SNAP software](https://step.esa.int/main/download/snap-download/) using [TOML](https://toml.io/en/) config files as input files. No additional Python libraries are required as pysnap-toolbox uses Python standard libraries starting from Python 3.11.

The goal of this script is to allow users to easily create and share SNAP processing workflows. This skips the clutter that is in XML graphs and allows users to focus only on the important aspects such as choosing the operator, sources, and relevant parameters. If no parameters are specified then processing will use the default values which are defined by SNAP.

# Unique tools
## Custom SNAP operators
Custom operators allow users to use popular community-generated workflows or workflows done by third-party software such as [SNAPHU](http://web.stanford.edu/group/radar/softwareandlinks/sw/snaphu/). As of now, the only custom operator is `SnaphuUnwrapping` which
automates transferring all the files to the SNAPHU bin directory for unwrapping, copying the command from the `snaphu.conf` file and running it, then copying it back to the original `SnaphuExport` directory.

## Filename management
The TOML input file only needs a source key for each workflow subtable. Filename management is automatically managed and follows the SNAP file naming conventions when possible.

## Automated cleanup
If specified, pysnap-toolbox can automatically cleanup intermediate scratch files generated during processing to help minimize the space consumed by the data.
# SNAP XML vs pysnap-toolbox TOML

Here is a small sample comparing SNAP's native XML graph vs pysnap-toolbox's TOML config. We are applying these steps:

1. TOPSAR-Split
2. Apply-Orbit-File

pysnaptoolbox's TOML config file:
```toml
[[workflow.image1]]
source = "image1.zip"
operator = "TOPSAR-Split"
parameters = {subswath="IW2", firstBurstIndex=8, lastBurstIndex=9, selectedPolarisations="VV"}

[[workflow.image1]]
operator = "Apply-Orbit-File"
parameters = {orbitType="Sentinel Precise (Auto Download)", continueOnFail=false}
```

SNAP XML Graph file:
```xml
<graph id="Graph">
  <version>1.0</version>
  <node id="Read">
    <operator>Read</operator>
    <sources/>
    <parameters class="com.bc.ceres.binding.dom.XppDomElement">
      <useAdvancedOptions>false</useAdvancedOptions>
      <file>image1.zip</file>
      <copyMetadata>true</copyMetadata>
      <bandNames/>
      <pixelRegion>0,0,2147483647,2147483647</pixelRegion>
      <maskNames/>
    </parameters>
  </node>
  <node id="TOPSAR-Split">
    <operator>TOPSAR-Split</operator>
    <sources>
      <sourceProduct refid="Read"/>
    </sources>
    <parameters class="com.bc.ceres.binding.dom.XppDomElement">
      <subswath/>
      <selectedPolarisations/>
      <firstBurstIndex>1</firstBurstIndex>
      <lastBurstIndex>9999</lastBurstIndex>
      <wktAoi/>
    </parameters>
  </node>
  <node id="Apply-Orbit-File">
    <operator>Apply-Orbit-File</operator>
    <sources>
      <sourceProduct refid="TOPSAR-Split"/>
    </sources>
    <parameters class="com.bc.ceres.binding.dom.XppDomElement">
      <orbitType>Sentinel Precise (Auto Download)</orbitType>
      <polyDegree>3</polyDegree>
      <continueOnFail>false</continueOnFail>
    </parameters>
  </node>
  <node id="Write">
    <operator>Write</operator>
    <sources>
      <sourceProduct refid="Apply-Orbit-File"/>
    </sources>
    <parameters class="com.bc.ceres.binding.dom.XppDomElement">
      <file>output.dim</file>
      <formatName>BEAM-DIMAP</formatName>
    </parameters>
  </node>
  <applicationData id="Presentation">
    <Description/>
    <node id="Read">
            <displayPosition x="40.0" y="138.0"/>
    </node>
    <node id="TOPSAR-Split">
      <displayPosition x="149.0" y="137.0"/>
    </node>
    <node id="Apply-Orbit-File">
      <displayPosition x="282.0" y="139.0"/>
    </node>
    <node id="Write">
            <displayPosition x="455.0" y="135.0"/>
    </node>
  </applicationData>
</graph>
```