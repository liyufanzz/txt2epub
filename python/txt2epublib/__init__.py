#!/usr/bin/python
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# copyright 2011 Mario Frasca

import os, os.path
import codecs
import zipfile
import tempfile
from docutils.core import publish_string
import re
from shutil import copyfile
import pkg_resources


def encode_entities(text):
    return text.replace(
        "&", "&amp;").replace(
        ">", "&gt;").replace(
        "<", "&lt;").replace(
        "\014", "")


def main(destination, sources, **options):
    """translate the files to epub
    """

    names = [os.path.basename(".".join(i.split('.')[:-1])).replace(" ", "_")
             for i in sources]
    types = [i.split('.')[-1].lower()
             for i in sources]
    options['names'] = names

    tempdir = tempfile.mkdtemp()
    ## create directory structure
    os.mkdir(tempdir + "/META-INF")
    os.mkdir(tempdir + "/content")

    ## create hard coded files
    out = open(tempdir + "/mimetype", "w")
    out.write("application/epub+zip")
    out.close()

    out = open(tempdir + "/META-INF/container.xml", "w")
    out.write("""<?xml version='1.0' encoding='utf-8'?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
    <rootfile media-type="application/oebps-package+xml" full-path="content/00_content.opf"/>
  </rootfiles>
</container>
""")
    out.close()

    ## use templates to produce rest of output
    from jinja2 import Environment, PackageLoader
    env = Environment(loader=PackageLoader(__name__, "templates"))

    ## start with content/00_content.opf
    template = env.get_template("00_content.opf")
    out = file(tempdir + "/content/00_content.opf", "w")
    out.write(template.render(options))
    out.close()

    ## then content/00_toc.ncx
    template = env.get_template("00_toc.ncx")
    out = file(tempdir + "/content/00_toc.ncx", "w")
    out.write(template.render(options))
    out.close()

    ## and the style
    template = env.get_template("00_stylesheet.css")
    out = file(tempdir + "/content/00_stylesheet.css", "w")
    out.write(template.render(options))
    out.close()

    ## then convert each of the files
    if options['keep_line_breaks']:
        template = env.get_template("item-br.html")
        split_on = '\n'
    else:
        template = env.get_template("item.html")
        split_on = '\n\n'
    included = []
    for short, full, this_type in zip(names, sources, types):
        if this_type == "png":
            copyfile(full, tempdir + "/content/" + short + ".png")
            included.append(short + ".png")
            continue
        
        info = {'title': short}
        content = codecs.open(full, encoding='utf-8').read()
        if this_type == "rst":
            text = publish_string(content, writer_name="html")
            pattern = re.compile('^(<html .*?) lang=".."(.*?>)$')
            text_lines = text.split("\n")
            matches = [pattern.match(l) for l in text_lines]
            try:
                (l, r) = [(l, r) for (l, r) in enumerate(matches) if r is not None][0]
                text_lines[l] = ''.join(r.groups())
                text = '\n'.join(text_lines)
            except:
                pass
        else:
            content = encode_entities(content)
            lines = content.split(split_on)
            info['lines'] = lines
            text = template.render(info)
        out = codecs.open(tempdir + "/content/" + short + ".html", "w", encoding='utf-8')
        out.write(text)
        out.close()
        included.append(short + ".html")

    ## finally zip everything into the destination
    out = zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED)
    out.write(tempdir + "/mimetype", "mimetype", zipfile.ZIP_STORED)
    out.write(tempdir + "/META-INF/container.xml", "META-INF/container.xml", zipfile.ZIP_DEFLATED)
    for name in ["00_content.opf", "00_stylesheet.css"] + included + ["00_toc.ncx"]:
        out.write(tempdir + "/content/" + name, "content/" + name, zipfile.ZIP_DEFLATED)
        
    out.close()
