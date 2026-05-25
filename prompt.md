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
[x] The unit of `EXPANSION SIZE` is (mm), not (m). Need to change the input of algorithm is mm not m.
[x] When I import aedt file, I cannot read or get all Nets. But if I import brd file, I canot get all Nets. Please fix it, I want both can get all Nets from file no matter what it is brd file or adet file.
[x] Original `EXPANSION` in Ansys use proportion for unit, which is meant to expand outward default value 10 percent(so the value is 0.1), the setting in Ansys is @expansion.png. Please modify relevant items.
[x] Expansion should use `expansion_factor` not `expansion_size` from @expansion.png. Please refer to ## Source and modify the code for cutout.
[x] Please change to `expansion_factor` not `expansion_size` for `ConvexHull` and `Bounding` like `Conforming`. This should be same as Ansys EM default operation.
[x] I want put the parts(adaptive_solutions.png) to above and have a section that is `adaptive_solutions` to make audience to know that is `adaptive_solutions` and the others are `Sweep`
[x] Add Ansys version since 2023.1 to latest version at ## Source
[x] Build a batch file, let me can directly use this transform tool to build one exe file from python file fro some code or feautures updated in the future.
[x] I found ansysedt.exe path or relevant ansys files are depend on the version of ansys, after 2025 the C:\Program Files\ANSYS Inc\{version}\AnsysEM. If before 2024(including 2024), the path is C:\Program Files\AnsysEM\{version}\Win64. The variable environment for example like @version_path.png. Please fix them according to different version
[x] I got some error when I use older version before 2024(including 2024) like 2021.1 for Apply Sweep setup `[SWEEP] Starting frequency sweep configuration...
Launching HFSS 3D Layout (non-graphical=True) to configure frequency sweep...
Edb connection closed.
C:\Users\pricewu\Documents\pyaedt_atg\.venv\Lib\site-packages\ansys\aedt\core\desktop.py:2382: UserWarning: PyAEDT has limited capabilities when used with an AEDT version earlier than 2022 R2.
                Update your AEDT installation to 2022 R2 or later.
  warnings.warn(
Error configuring sweep via PyAEDT:
Traceback (most recent call last):
File "c:\Users\pricewu\Documents\pyaedt_atg\aedt_utils.py", line 288, in setup_broadband_sweep
    h3d = Hfss3dLayout(project=self.edb_path, version=self.version, non_graphical=non_graphical)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\pricewu\Documents\pyaedt_atg\.venv\Lib\site-packages\ansys\aedt\core\hfss3dlayout.py", line 173, in __init__
    FieldAnalysis3DLayout.__init__(
File "C:\Users\pricewu\Documents\pyaedt_atg\.venv\Lib\site-packages\ansys\aedt\core\application\analysis_3d_layout.py", line 129, in __init__
    Analysis.__init__(
File "C:\Users\pricewu\Documents\pyaedt_atg\.venv\Lib\site-packages\ansys\aedt\core\application\analysis.py", line 145, in __init__
    Design.__init__(
File "C:\Users\pricewu\Documents\pyaedt_atg\.venv\Lib\site-packages\ansys\aedt\core\application\design.py", line 207, in __init__
    self._desktop_class = self.__init_desktop_from_design(
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\pricewu\Documents\pyaedt_atg\.venv\Lib\site-packages\ansys\aedt\core\application\design.py", line 4399, in __init_desktop_from_design
    return Desktop(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\pricewu\Documents\pyaedt_atg\.venv\Lib\site-packages\ansys\aedt\core\desktop.py", line 749, in __init__
    self.check_starting_mode()
File "C:\Users\pricewu\Documents\pyaedt_atg\.venv\Lib\site-packages\ansys\aedt\core\generic\general_methods.py", line 256, in wrapper
    return raise_exception_or_return_false(e)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\pricewu\Documents\pyaedt_atg\.venv\Lib\site-packages\ansys\aedt\core\generic\general_methods.py", line 218, in raise_exception_or_return_false
    raise e
File "C:\Users\pricewu\Documents\pyaedt_atg\.venv\Lib\site-packages\ansys\aedt\core\generic\general_methods.py", line 231, in wrapper
    out = user_function(*args, **kwargs)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\pricewu\Documents\pyaedt_atg\.venv\Lib\site-packages\ansys\aedt\core\desktop.py", line 949, in check_starting_mode
    raise Exception("Unsupported AEDT version")
Exception: Unsupported AEDT version
Opening EDB folder C:/Users/pricewu/Documents/pyaedt_atg/G651-15140-06_FL5_CLB_2_cutout.aedb...
[SWEEP] Failed to configure sweep via PyAEDT. Please check logs.`
please fix it, and tell me what happended
[x] Update the `User Guide` tab and @README.md after modification or feautures added.