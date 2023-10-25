import sys
import maya.cmds as cmds

from PySide2 import QtWidgets
from PySide2.QtWidgets import QPushButton


def get_selected_locators():
    selected = cmds.ls(sl=True, tr=True) or []
    selected_locators = []
    for obj in selected:
        if cmds.listRelatives(obj, shapes=True, type="locator"):
            selected_locators.append(obj)
    if len(selected_locators) == 0:
        print("No locators selected")
    return selected_locators


def create_joints():
    joints = []
    selected_locators = get_selected_locators()
    if len(selected_locators) > 1:
        cmds.select(d=True)
        position = cmds.pointPosition(selected_locators[0])
        cmds.delete(selected_locators[0])
        selected_locators.pop(0)
        previous_joint = cmds.joint(p=position)
        joints.append(previous_joint)

        for loc in selected_locators:
            cmds.joint(previous_joint, e=True, zso=True, oj="xyz")
            position = cmds.pointPosition(loc)
            previous_joint = cmds.joint(p=position)
            joints.append(previous_joint)
            cmds.delete(loc)
    return joints[0]


def create_ik_chain(base_joints):
    joints = cmds.duplicate(base_joints, rc=True)

    ik_handle = cmds.ikHandle(sj=joints[0], ee=joints[len(joints) - 2])

    circle = cmds.circle(nr=[0, 1, 0], r=3)
    cmds.parent(circle[0], joints[len(joints) - 2])
    cmds.CenterPivot(circle)
    cmds.makeIdentity(circle, apply=False, t=1, r=1, s=1)
    cmds.parent(circle[0], w=True)

    cmds.parent(ik_handle[0], circle[0])

    circle = cmds.rename(circle[0], "ik_control")

    cmds.group(
        joints[0], circle, n="IK_Chain", p=cmds.listRelatives(base_joints, p=True)[0]
    )
    cmds.hide(joints)
    return joints[0]


def create_fk_chain(base_joints):
    joints = cmds.duplicate(base_joints, rc=True)
    circles = []
    for index, joint in enumerate(joints):
        if index < len(joints)-1:
            circle = cmds.circle(
                nr=find_direction_vector(joint, joints[index + 1]), r=1
            )
            circles.append(circle)
            cmds.parent(circle[0], joint)
            cmds.makeIdentity(circle, t=1, r=1, s=1)
            cmds.parent(circle[0], w=True)

            cmds.parentConstraint(circle[0], joint, mo=True)

    for index, circle in reversed(list(enumerate(circles))):
        if index > 0:
            cmds.parent(circle, circles[index - 1])

    cmds.group(
        joints[0],
        circles[0],
        n="FK_Chain",
        p=cmds.listRelatives(base_joints, p=True)[0],
    )
    for circle in circles:
        cmds.rename(circle[0], "fk_control")

    cmds.hide(joints)
    return joints[0]


def find_direction_vector(joint1, joint2):
    pos1 = cmds.joint(joint1, q=True, p=True)
    pos2 = cmds.joint(joint2, q=True, p=True)

    return [pos2[0] - pos1[0], pos2[1] - pos1[1], pos2[2] - pos1[2]]


def create_ik_fk_control(base, ik, fk):

    # Creates a locator with the settings for the weight between IK and FK
    control = cmds.spaceLocator(name="ikfk_blend_control")
    cmds.addAttr(
        control,
        longName="IKFK",
        minValue=0,
        maxValue=1,
        defaultValue=0.5,
        attributeType="double",
    )
    cmds.setAttr(control[0] + ".IKFK", edit=True, keyable=True)

    # Connects the respective joints in each chain to the values of the blend node
    for idx, joint in enumerate(base):
        blender = cmds.createNode("blendColors", n=(joint + "_ik_fk_blend"))
        cmds.connectAttr(ik[idx] + ".rotate", blender + ".color1", f=True)
        cmds.connectAttr(fk[idx] + ".rotate", blender + ".color2", f=True)
        cmds.connectAttr(blender + ".output", joint + ".rotate", f=True)
        cmds.connectAttr(control[0] + ".IKFK", blender + ".blender", f=True)

    return control


def rename_joint_lists(base, ik, fk):
    base_joints = cmds.listRelatives(base, ad=True, type="joint")
    base_joints.insert(0, base)
    base_joints.sort()
    ik_joints = cmds.listRelatives(ik, ad=True, type="joint")
    ik_joints.append(ik)
    ik_joints.sort()
    fk_joints = cmds.listRelatives(fk, ad=True, type="joint")
    fk_joints.append(fk)
    fk_joints.sort()

    for idx in range(0, len(base_joints)):
        base_joints[idx] = cmds.rename(base_joints[idx], "base_joint_{0}".format(idx))
        ik_joints[idx] = cmds.rename(ik_joints[idx], "ik_joint_{0}".format(idx))
        fk_joints[idx] = cmds.rename(fk_joints[idx], "fk_joint_{0}".format(idx))
    return base_joints, fk_joints, ik_joints


def run_tool():

    base = create_joints()
    cmds.group(base, n="IKFKTest")
    ik = create_ik_chain(base)
    fk = create_fk_chain(base)
    base, ik, fk = rename_joint_lists(base, ik, fk)

    control = create_ik_fk_control(base, ik, fk)
    cmds.parent(control, cmds.listRelatives(base[0], p=True))


# Create the Qt Application if it doesn't already exist
if not QtWidgets.QApplication.instance():
    app = QtWidgets.QApplication(sys.argv)
else:
    app = QtWidgets.QApplication.instance()
# Create a button, connect it and show it
button = QPushButton("Run tool")
button.clicked.connect(run_tool)
button.show()
# Run the main Qt loop
app.exec_()
