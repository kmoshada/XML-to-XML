import xml.etree.ElementTree as ET
from datetime import datetime
import flet as ft
import os

# Register namespaces for output schema
ET.register_namespace('', "http://www.elsevier.com/xml/ani/ani")
ET.register_namespace('ce', "http://www.elsevier.com/xml/ani/common")

def build_elsevier_xml(meta):
    # root
    root = ET.Element('units', {
        'xmlns': 'http://www.elsevier.com/xml/ani/ani',
        'xmlns:ce': 'http://www.elsevier.com/xml/ani/common'
    })

    # BATCH unit
    unit = ET.SubElement(root, 'unit', {'type': 'BATCH'})
    ui = ET.SubElement(unit, 'unit-info')
    ET.SubElement(ui, 'unit-id').text = '1'
    ET.SubElement(ui, 'order-id').text = 'unknown'
    ET.SubElement(ui, 'parcel-id').text = 'none'
    ET.SubElement(ui, 'supplier-id').text = '4'
    ET.SubElement(ui, 'timestamp').text = datetime.utcnow().isoformat() + 'Z'

    # content
    uc = ET.SubElement(unit, 'unit-content')
    bib = ET.SubElement(uc, 'bibrecord')

    # item-info
    ii = ET.SubElement(bib, 'item-info')
    ET.SubElement(ii, 'status', {'state': 'new','stage':'S300'})
    idl = ET.SubElement(ii, 'itemidlist')
    ET.SubElement(idl, 'ce:doi').text = meta['doi']
    ET.SubElement(idl, 'itemid', {'idtype':'TPA-ID'}).text = '2025901569576X'
    ET.SubElement(idl, 'itemid', {'idtype':'IPUI'}).text = '2039057815'

    # head
    head = ET.SubElement(bib, 'head')
    # citation-info
    ci = ET.SubElement(head, 'citation-info')
    ET.SubElement(ci, 'citation-type', {'code':'ar'})
    ET.SubElement(ci, 'citation-language', {'xml:lang':'ENG'})
    ET.SubElement(ci, 'abstract-language', {'xml:lang':'ENG'})
    ak = ET.SubElement(ci, 'author-keywords')
    for kw in meta['keywords']:
        ET.SubElement(ak, 'author-keyword').text = kw

    # title
    ct = ET.SubElement(head, 'citation-title')
    ET.SubElement(ct, 'titletext', {'xml:lang':'ENG','original':'y'}).text = meta['full_title']

    # journal source
    src = ET.SubElement(head, 'source', {'srcid':'UNKNOWN'})
    vip = ET.SubElement(src, 'volisspag')
    vin = ET.SubElement(vip, 'volume-issue-number')
    ET.SubElement(vin, 'vol-first').text = meta['volume']
    pii = ET.SubElement(vip, 'page-information')
    pg = ET.SubElement(pii, 'pages')
    ET.SubElement(pg, 'first-page').text = meta['elocation'] or ''
    puby = ET.SubElement(src, 'publicationyear', {'first': meta['pub_dates'].get('ppub','')[:4]})
    pdate = ET.SubElement(src, 'publicationdate')
    fdate = meta['pub_dates'].get('final', meta['pub_dates'].get('ppub',''))
    y,m,d = fdate.split('-') if '-' in fdate else ('','','')
    ET.SubElement(pdate, 'year').text = y
    ET.SubElement(pdate, 'month').text = m
    ET.SubElement(pdate, 'day').text = d

    # license
    if meta['license_text']:
        lic = ET.SubElement(head, 'license')
        lic.text = meta['license_text']

    # authors + affiliations
    for i,a in enumerate(meta['authors'], start=1):
        ag = ET.SubElement(head, 'author-group', {'seq':str(i)})
        au = ET.SubElement(ag, 'author', {'seq':str(i)})
        if a['orcid']: au.set('orcid', a['orcid'])
        ET.SubElement(au, 'ce:initials').text = a['initials']
        ET.SubElement(au, 'ce:surname').text = a['surname']
        if a['email']: ET.SubElement(au, 'ce:e-address').text = a['email']
        aid = a['aff_id']
        if aid in meta['affiliations']:
            aff_node = meta['affiliations'][aid]
            aff_el = ET.SubElement(ag, 'affiliation')
            for inst in aff_node.findall('.//institution'):
                ET.SubElement(aff_el, 'organization').text = inst.text
            for st in aff_node.findall(".//named-content[@content-type='street']"):
                ET.SubElement(aff_el, 'address-part').text = st.text
            ET.SubElement(aff_el, 'city').text = aff_node.findtext(".//named-content[@content-type='city']", '')
            ET.SubElement(aff_el, 'postal-code').text = aff_node.findtext(".//named-content[@content-type='postcode']", '')
            country = aff_node.findtext('.//country', '')
            ET.SubElement(aff_el, 'country', {'iso-code':''}).text = country

    # correspondence
    for a in meta['authors']:
        if a['corresp']:
            cor = ET.SubElement(head, 'correspondence')
            person = ET.SubElement(cor, 'person')
            ET.SubElement(person, 'ce:initials').text = a['initials']
            ET.SubElement(person, 'ce:surname').text = a['surname']
            if a['email']: ET.SubElement(cor, 'ce:e-address').text = a['email']

    # abstracts
    abs_section = ET.SubElement(head, 'abstracts')
    ab = ET.SubElement(abs_section, 'abstract', {'original':'y','xml:lang':'ENG'})
    ET.SubElement(ab, 'publishercopyright').text = '© The Authors 2025'
    ET.SubElement(ab, 'ce:para').text = meta['abstract']

    # figures
    if meta['figures']:
        figs_el = ET.SubElement(bib, 'figures')
        for fig in meta['figures']:
            fe = ET.SubElement(figs_el, 'figure', {'id': fig['id']})
            ET.SubElement(fe, 'caption').text = fig['caption']

    return root

def extract_jats_metadata(jats_root):
    meta = {}
    meta['doi'] = jats_root.findtext(".//article-id[@pub-id-type='doi']", default='unknown')
    meta['title'] = jats_root.findtext(".//title-group/article-title", default='').strip()
    meta['subtitle'] = jats_root.findtext(".//title-group/subtitle", default='').strip()
    meta['full_title'] = f"{meta['title']} {meta['subtitle']}".strip()

    abstract = jats_root.find(".//abstract")
    meta['abstract'] = ' '.join([p.text.strip() for p in abstract.findall("p") if p.text]) if abstract is not None else ''
    meta['keywords'] = [kw.text for kw in jats_root.findall(".//kwd-group/kwd") if kw.text]

    journal = jats_root.find('.//journal-meta')
    meta['journal_title'] = journal.findtext('journal-title-group/journal-title', default='')
    meta['journal_abbrev'] = journal.findtext('journal-title-group/abbrev-journal-title', default='')
    meta['issn_ppub'] = journal.findtext("issn[@pub-type='ppub']", default='')
    meta['issn_epub'] = journal.findtext("issn[@pub-type='epub']", default='')
    meta['publisher'] = journal.findtext('publisher/publisher-name', default='')

    art_meta = jats_root.find('.//article-meta')
    meta['volume'] = art_meta.findtext('volume', default='')
    meta['issue'] = art_meta.findtext("issue-id[@pub-id-type='publisher-id']", default='')
    meta['elocation'] = art_meta.findtext('elocation-id', default='')

    meta['pub_dates'] = {}
    for pd in art_meta.findall('pub-date'):
        ptype = pd.attrib.get('pub-type')
        day = pd.findtext('day', default='')
        month = pd.findtext('month', default='')
        year = pd.findtext('year', default='')
        meta['pub_dates'][ptype] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    lic = art_meta.find('permissions/license')
    meta['license_text'] = ' '.join([lp.text for lp in lic.findall('.//ext-link') if lp.text]) if lic is not None else ''

    meta['figures'] = []
    for fig in jats_root.findall('.//fig'):
        caption = fig.findtext('caption//p', default='').strip()
        fid = fig.attrib.get('id', '')
        meta['figures'].append({'id': fid, 'caption': caption})

    meta['authors'] = []
    meta['affiliations'] = {}
    for aff in jats_root.findall('.//aff'):
        aid = aff.attrib.get('id', f'aff{len(meta["affiliations"])}')
        meta['affiliations'][aid] = aff

    for contrib in jats_root.findall('.//contrib-group/contrib'):
        author = {
            'orcid': '',
            'initials': contrib.findtext('.//given-names', default=''),
            'surname': contrib.findtext('.//surname', default=''),
            'email': contrib.findtext('.//email', default=''),
            'aff_id': contrib.findtext(".//xref[@ref-type='aff']", default=''),
            'corresp': contrib.attrib.get('corresp', '') == 'yes'
        }
        orcid = contrib.find('.//contrib-id')
        if orcid is not None and 'orcid.org' in orcid.text:
            author['orcid'] = orcid.text.split('/')[-1]
        meta['authors'].append(author)

    return meta

def run_app(page: ft.Page):
    page.title = "JATS to Elsevier XML Converter"
    page.scroll = ft.ScrollMode.AUTO

    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)

    result_text = ft.Text(value="", color=ft.Colors.GREEN, selectable=True)

    def convert_jats_to_elsevier(input_path: str, output_path: str):
        tree = ET.parse(input_path)
        root = tree.getroot()
        meta = extract_jats_metadata(root)
        out_root = build_elsevier_xml(meta)
        ET.ElementTree(out_root).write(output_path, encoding='utf-8', xml_declaration=True)
        result_text.value = f"✅ Converted and saved to {output_path}"
        page.update()

    def pick_file_result(e: ft.FilePickerResultEvent):
        if e.files:
            input_path = e.files[0].path
            output_path = os.path.splitext(input_path)[0] + "_converted.xml"
            convert_jats_to_elsevier(input_path, output_path)

    file_picker.on_result = pick_file_result

    page.add(
        ft.Column([
            ft.Text("Convert JATS XML to Elsevier XML", size=20, weight="bold"),
            ft.ElevatedButton("Choose Input XML File", on_click=lambda _: file_picker.pick_files(allow_multiple=False)),
            result_text
        ])
    )

if __name__ == "__main__":
    ft.app(target=run_app)