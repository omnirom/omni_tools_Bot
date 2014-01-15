import sys
import lxml.etree


def main(path):
    xmltext = open(path).read()
    xml = lxml.etree.fromstring(xmltext)
    for project in xml.xpath('//project'):
        # Default remote is AOSP, but we'll skip explicit
        # aosp references as well
        if 'remote' in project.attrib and project.attrib['remote'] != 'aosp':
            print(project.attrib['path'])


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: %s <path to manifest.xml>" % sys.argv[0])
        sys.exit(1)
    main(sys.argv[1])
