## Source
- https://aedt.docs.pyansys.com/
- https://github.com/ansys/pyaedt
- https://aedt.docs.pyansys.com/version/stable/API/index.html

## Sample
- G651-19063-03_TEST22.brd
- netlist or netname tentatively use related to ANT6 for easily test. You also can use relevant ANT7 to test

## Environments
- python virtual environment: .venv
- Ansys version: Ansys Electronics Desktop 2025 R1
- Ansys EM location: C:\Program Files\ANSYS Inc\v251\AnsysEM

## Requirements
- Build a GUI tool that is user-friendly, easily use, good design, good visualized GUI interface
- Want to solve the complicated process to set layout cutout, port setting for RLC and excitation and Freq range for Braodbaand
- Give the default value setting and first sight to know how to operate parameters
- Give the netname or netlist, it can automatically to find the components and set the port according to its components' pins or ports
- If the component is RLC of shunt, it can find the nearest GND to set it
- If the component is RLC of series, it also can use the edge to set the port
- The setting of port can use `Create ports on component`, `circuit port`, general `edge port` or other suitable port.
- You can follow all the Guide in ## Source
- Compatible all the version of Ansys
- Main purpose is given a brd or adet file and help complete all the setting with default(or good to operate the parameters) before starting to analyze the EM

## Design process for the tool
- You can use SDD developments like spec, plan, clarify, task, implement
- You also use opencode developments process
- It MUST have guide or redame to tell audience how to use it after complete this tool

## Test
- Sanity check test
- Unit Test
- Integration Test
- System Test
- E2E test
- White Box Test
- Black Box Test
- Gray Box Test

## Issues and Feautures need to be modified or improved. [x] means the item is finished
[x] `Cutout type` default is `Coforming`
[x] `Expansion Size` default is `0.05`
[x] The color of background and font in MessageBox is simialr, so audidence cannot see the message clearly, please change the color of font
[x] Add Adaptive Solutions in `Sweep` tab. There are three types for Solution Frequency: `Single`, `Multi-frequencies`, `Broadband`. Default type is `Broadband`. Use dropdownBox to acommodate them. Moremore, when select different type, the default parameters are different by Ansys settings needed for `Adaptvie Solutions`.
[x] Port setting:
    [x] 1. Remove the `circuit_ port` because I found it is not as my expectation
    [x] 2. I also fund some termination points for components are not assigned the excitation like red circle pointed @termination.png, please help fix them.
    [x] 3. Based on above 1. and 2., If you have better `Port Generation Mode` methods, you also can add it in.
[x] Remove `Ports on Terminations + Passive RLCs` because this results are not as my expectation.
[x] When Creating Terminations ports, it MUST use the same layer Gnd as reference because I find out sometimes it will choose different layer even use GND which is far from other original wanted termination.
[x] Adaptive Solutions: there are three types for There are three types for Solution Frequency: `Single`, `Multi-frequencies`, `Broadband`. I have the Ansys setting picture on it for those three types respectively. @Single.png, @multi-frequencies.png, @BraodBand.png. Please help modify or add them in `4. Sweep` tab. Default `Low frequency` is 0.5GHz and `High frequency` is 5GHz for `Broadband`.
[x] Add `Analyze` button and its function. I can begin run the EM simulation if I check everything is fine. Remember not to make the tool be frozen when running a long time on it.
[x] Termination port is too close other port like @term1.png, I hope you can change another way to be like @term2.png for termination port.
[x] Add a feature that import wanted stackup file .xml to the board like Ansys operation @stackup.png. This is optional function. We can insert this feature in `Cutout` tab. @ASK5_CLB_Cu_5E7_DIEL_FILL.xml as the sample for use and examination.
[x] After finishing the EM analysis, export Matrix Data of Touchstone(.sNp) automatically
[x] After Cutout with import @ASK5_CLB_Cu_5E7_DIEL_FILL.xml, Something is off becasue the part of material is empty like @stackup1.png. I try to import it manually, the material is right like @stackup2.png. Please fix it.
[x] Automatically detect how many port for the simulation, so it can use the right snp port file such as .s10p s16p for 10 and 16 ports respectively, not hard extended file name .sNp file. 
[x] Update the `User Guide` tab and @README.md after modification or feautures added.