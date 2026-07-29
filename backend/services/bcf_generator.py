import io
import uuid
import zipfile
import xml.etree.ElementTree as ET
from xml.dom import minidom
from PIL import Image, ImageDraw

BCF_VERSION = "2.1"

def pretty_xml(elem):
    rough = ET.tostring(elem, encoding="unicode")
    reparsed = minidom.parseString(rough)
    return reparsed.toprettyxml(indent="  ", encoding=None).replace('<?xml version="1.0" ?>\n', '')

def make_bcf_version():
    root = ET.Element("Version", VersionId=BCF_VERSION)
    ET.SubElement(root, "DetailedVersion").text = BCF_VERSION
    return pretty_xml(root)

def make_project_bcfp(project_name, project_id):
    root = ET.Element("ProjectExtension")
    proj = ET.SubElement(root, "Project", ProjectId=project_id)
    ET.SubElement(proj, "Name").text = project_name
    ET.SubElement(root, "ExtensionSchema").text = ""
    return pretty_xml(root)

def make_markup(topic):
    root = ET.Element("Markup")

    header = ET.SubElement(root, "Header")
    file_el = ET.SubElement(header, "File", IfcProject=topic.get("ifc_project_guid", ""), isExternal="false")
    ET.SubElement(file_el, "Filename").text = "model.ifc"
    ET.SubElement(file_el, "Date").text = topic["creation_date"]
    ET.SubElement(file_el, "Reference").text = "../model.ifc"

    t = ET.SubElement(root, "Topic", Guid=topic["guid"], TopicType=topic["type"], TopicStatus=topic["status"])
    ET.SubElement(t, "Title").text = topic["title"]
    ET.SubElement(t, "Priority").text = topic["priority"]
    ET.SubElement(t, "CreationDate").text = topic["creation_date"]
    ET.SubElement(t, "CreationAuthor").text = topic["author"]
    ET.SubElement(t, "ModifiedDate").text = topic["modified_date"]
    ET.SubElement(t, "ModifiedAuthor").text = topic["author"]
    if topic.get("description"):
        ET.SubElement(t, "Description").text = topic["description"]

    vp = ET.SubElement(root, "Viewpoints", Guid=topic["guid"])
    ET.SubElement(vp, "Viewpoint").text = "viewpoint.bcfv"
    ET.SubElement(vp, "Snapshot").text = "snapshot.png"
    ET.SubElement(vp, "Index").text = "0"

    for c in topic.get("comments", []):
        comment = ET.SubElement(root, "Comment", Guid=str(uuid.uuid4()))
        ET.SubElement(comment, "Date").text = topic["creation_date"]
        ET.SubElement(comment, "Author").text = topic["author"]
        ET.SubElement(comment, "Comment").text = c
        ET.SubElement(comment, "Viewpoint", Guid=topic["guid"])

    return pretty_xml(root)

def make_viewpoint(topic):
    root = ET.Element("VisualizationInfo", Guid=topic["guid"])
    components = ET.SubElement(root, "Components")
    ET.SubElement(components, "ViewSetupHints", SpacesVisible="false", SpaceBoundariesVisible="false", OpeningsVisible="false")

    if topic.get("component_guids"):
        selection = ET.SubElement(components, "Selection")
        for gid in topic["component_guids"][:10]:
            comp = ET.SubElement(selection, "Component", IfcGuid=gid)
            ET.SubElement(comp, "OriginatingSystem").text = "IFC Semantic Data-Loss Analyser"
            ET.SubElement(comp, "AuthoringToolId").text = gid

        coloring = ET.SubElement(components, "Coloring")
        color_el = ET.SubElement(coloring, "Color", Color="FF0000")
        for gid in topic["component_guids"][:10]:
            comp = ET.SubElement(color_el, "Component", IfcGuid=gid)
            ET.SubElement(comp, "OriginatingSystem").text = "IFC Semantic Data-Loss Analyser"

    visibility = ET.SubElement(components, "Visibility", DefaultVisibility="true")
    ET.SubElement(visibility, "Exceptions")

    camera = ET.SubElement(root, "PerspectiveCamera")
    vp_loc = ET.SubElement(camera, "CameraViewPoint")
    ET.SubElement(vp_loc, "X").text = "0.0"
    ET.SubElement(vp_loc, "Y").text = "-10.0"
    ET.SubElement(vp_loc, "Z").text = "5.0"
    vp_dir = ET.SubElement(camera, "CameraDirection")
    ET.SubElement(vp_dir, "X").text = "0"
    ET.SubElement(vp_dir, "Y").text = "1"
    ET.SubElement(vp_dir, "Z").text = "-0.5"
    vp_up = ET.SubElement(camera, "CameraUpVector")
    ET.SubElement(vp_up, "X").text = "0"
    ET.SubElement(vp_up, "Y").text = "0"
    ET.SubElement(vp_up, "Z").text = "1"
    ET.SubElement(camera, "FieldOfView").text = "60"

    return pretty_xml(root)

def generate_bcf_zip(issues: list) -> bytes:
    """
    Accepts a list of issues and generates a BCF zip file in memory.
    Each issue: {title, description, priority, type, status, author, component_guids}
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # BCF version file
        zip_file.writestr("bcf.version", make_bcf_version())
        # BCF project file
        zip_file.writestr("project.bcfp", make_project_bcfp("ArchiShield Audit Project", str(uuid.uuid4())))

        for idx, issue in enumerate(issues):
            topic_guid = str(uuid.uuid4())
            now_str = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            topic = {
                "guid": topic_guid,
                "title": issue.get("title", f"Issue {idx+1}"),
                "description": issue.get("description", ""),
                "priority": issue.get("priority", "Normal"),
                "type": issue.get("type", "Issue"),
                "status": issue.get("status", "Open"),
                "author": issue.get("author", "Auditor"),
                "creation_date": now_str,
                "modified_date": now_str,
                "component_guids": issue.get("component_guids", []),
                "comments": issue.get("comments", [])
            }

            folder = f"{topic_guid}/"
            zip_file.writestr(folder + "markup.bcf", make_markup(topic))
            zip_file.writestr(folder + "viewpoint.bcfv", make_viewpoint(topic))

            # Draw a simple placeholder image for the snapshot
            img = Image.new("RGB", (300, 200), color=(13, 31, 61))
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), "IFC Data-Loss Issue", fill=(255, 255, 255))
            draw.text((10, 30), f"Title: {topic['title'][:35]}", fill=(255, 224, 102))
            draw.text((10, 50), f"Priority: {topic['priority']}", fill=(255, 107, 107))
            draw.text((10, 70), f"Component count: {len(topic['component_guids'])}", fill=(79, 195, 247))

            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            zip_file.writestr(folder + "snapshot.png", img_bytes.getvalue())

    return zip_buffer.getvalue()

import datetime
