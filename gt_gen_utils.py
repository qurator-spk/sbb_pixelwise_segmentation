import click
import sys
import os
import numpy as np
import warnings
import xml.etree.ElementTree as ET
from tqdm import tqdm
import cv2
from shapely import geometry
from pathlib import Path


KERNEL = np.ones((5, 5), np.uint8)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")

def get_content_of_dir(dir_in):
    """
    Listing all ground truth page xml files. All files are needed to have xml format.
    """

    gt_all=os.listdir(dir_in)
    gt_list=[file for file in gt_all if file.split('.')[ len(file.split('.'))-1 ]=='xml' ]
    return gt_list
    
def return_parent_contours(contours, hierarchy):
    contours_parent = [contours[i] for i in range(len(contours)) if hierarchy[0][i][3] == -1]
    return contours_parent
def filter_contours_area_of_image_tables(image, contours, hierarchy, max_area, min_area):
    found_polygons_early = list()

    jv = 0
    for c in contours:
        if len(c) < 3:  # A polygon cannot have less than 3 points
            continue

        polygon = geometry.Polygon([point[0] for point in c])
        # area = cv2.contourArea(c)
        area = polygon.area
        ##print(np.prod(thresh.shape[:2]))
        # Check that polygon has area greater than minimal area
        # print(hierarchy[0][jv][3],hierarchy )
        if area >= min_area * np.prod(image.shape[:2]) and area <= max_area * np.prod(image.shape[:2]):  # and hierarchy[0][jv][3]==-1 :
            # print(c[0][0][1])
            found_polygons_early.append(np.array([[point] for point in polygon.exterior.coords], dtype=np.int32))
        jv += 1
    return found_polygons_early

def filter_contours_area_of_image(image, contours, order_index, max_area, min_area):
    found_polygons_early = list()
    order_index_filtered = list()
    #jv = 0
    for jv, c in enumerate(contours):
        #print(len(c[0]))
        c = c[0]
        if len(c) < 3:  # A polygon cannot have less than 3 points
            continue
        c_e = [point for point in c]
        #print(c_e)
        polygon = geometry.Polygon(c_e)
        area = polygon.area
        #print(area,'area')
        if area >= min_area * np.prod(image.shape[:2]) and area <= max_area * np.prod(image.shape[:2]):  # and hierarchy[0][jv][3]==-1 :
            found_polygons_early.append(np.array([[point] for point in polygon.exterior.coords], dtype=np.uint))
            order_index_filtered.append(order_index[jv])
        #jv += 1
    return found_polygons_early, order_index_filtered

def return_contours_of_interested_region(region_pre_p, pixel, min_area=0.0002):

    # pixels of images are identified by 5
    if len(region_pre_p.shape) == 3:
        cnts_images = (region_pre_p[:, :, 0] == pixel) * 1
    else:
        cnts_images = (region_pre_p[:, :] == pixel) * 1
    cnts_images = cnts_images.astype(np.uint8)
    cnts_images = np.repeat(cnts_images[:, :, np.newaxis], 3, axis=2)
    imgray = cv2.cvtColor(cnts_images, cv2.COLOR_BGR2GRAY)
    ret, thresh = cv2.threshold(imgray, 0, 255, 0)

    contours_imgs, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    contours_imgs = return_parent_contours(contours_imgs, hierarchy)
    contours_imgs = filter_contours_area_of_image_tables(thresh, contours_imgs, hierarchy, max_area=1, min_area=min_area)

    return contours_imgs
def update_region_contours(co_text, img_boundary, erosion_rate, dilation_rate, y_len, x_len):
    co_text_eroded = []
    for con in co_text:
        #try:
        img_boundary_in = np.zeros( (y_len,x_len) )
        img_boundary_in = cv2.fillPoly(img_boundary_in, pts=[con], color=(1, 1, 1))
        #print('bidiahhhhaaa')
        
        
        
        #img_boundary_in = cv2.erode(img_boundary_in[:,:], KERNEL, iterations=7)#asiatica
        if erosion_rate > 0:
            img_boundary_in = cv2.erode(img_boundary_in[:,:], KERNEL, iterations=erosion_rate)
        
        pixel = 1
        min_size = 0
        con_eroded = return_contours_of_interested_region(img_boundary_in,pixel, min_size )
        
        try:
            co_text_eroded.append(con_eroded[0])
        except:
            co_text_eroded.append(con)
        

        img_boundary_in_dilated = cv2.dilate(img_boundary_in[:,:], KERNEL, iterations=dilation_rate)
        #img_boundary_in_dilated = cv2.dilate(img_boundary_in[:,:], KERNEL, iterations=5)
        
        boundary = img_boundary_in_dilated[:,:] - img_boundary_in[:,:]
        
        img_boundary[:,:][boundary[:,:]==1] =1
    return co_text_eroded, img_boundary
def get_images_of_ground_truth(gt_list, dir_in, output_dir, output_type, config_file, config_params):
    """
    Reading the page xml files and write the ground truth images into given output directory.
    """
    ## to do: add footnote to text regions
    for index in tqdm(range(len(gt_list))):
        #try:
        tree1 = ET.parse(dir_in+'/'+gt_list[index])
        root1=tree1.getroot()
        alltags=[elem.tag for elem in root1.iter()]
        link=alltags[0].split('}')[0]+'}'
                            
        
                            
        for jj in root1.iter(link+'Page'):
            y_len=int(jj.attrib['imageHeight'])
            x_len=int(jj.attrib['imageWidth'])
            
        if config_file and (config_params['use_case']=='textline' or config_params['use_case']=='word' or config_params['use_case']=='glyph' or config_params['use_case']=='printspace'):
            keys = list(config_params.keys())
            if "artificial_class_label" in keys:
                artificial_class_rgb_color = (255,255,0)
                artificial_class_label = config_params['artificial_class_label']
                
            textline_rgb_color = (255, 0, 0)
                
            if config_params['use_case']=='textline':
                region_tags = np.unique([x for x in alltags if x.endswith('TextLine')])
            elif config_params['use_case']=='word':
                region_tags = np.unique([x for x in alltags if x.endswith('Word')])
            elif config_params['use_case']=='glyph':
                region_tags = np.unique([x for x in alltags if x.endswith('Glyph')])
            elif config_params['use_case']=='printspace':
                region_tags = np.unique([x for x in alltags if x.endswith('PrintSpace')])
                
            co_use_case = []

            for tag in region_tags:
                if config_params['use_case']=='textline':
                    tag_endings = ['}TextLine','}textline']
                elif config_params['use_case']=='word':
                    tag_endings = ['}Word','}word']
                elif config_params['use_case']=='glyph':
                    tag_endings = ['}Glyph','}glyph']
                elif config_params['use_case']=='printspace':
                    tag_endings = ['}PrintSpace','}printspace']
                    
                if tag.endswith(tag_endings[0]) or tag.endswith(tag_endings[1]):
                    for nn in root1.iter(tag):
                        c_t_in = []
                        sumi = 0
                        for vv in nn.iter():
                            # check the format of coords
                            if vv.tag == link + 'Coords':
                                coords = bool(vv.attrib)
                                if coords:
                                    p_h = vv.attrib['points'].split(' ')
                                    c_t_in.append(
                                        np.array([[int(x.split(',')[0]), int(x.split(',')[1])] for x in p_h]))
                                    break
                                else:
                                    pass

                            if vv.tag == link + 'Point':
                                c_t_in.append([int(np.float(vv.attrib['x'])), int(np.float(vv.attrib['y']))])
                                sumi += 1
                            elif vv.tag != link + 'Point' and sumi >= 1:
                                break
                        co_use_case.append(np.array(c_t_in))
                        
                        
                        
            if "artificial_class_label" in keys:
                img_boundary = np.zeros((y_len, x_len))
                erosion_rate = 1
                dilation_rate = 3
                co_use_case, img_boundary = update_region_contours(co_use_case, img_boundary, erosion_rate, dilation_rate, y_len, x_len )
            
                
            img = np.zeros((y_len, x_len, 3))
            if output_type == '2d':
                img_poly = cv2.fillPoly(img, pts=co_use_case, color=(1, 1, 1))
                if "artificial_class_label" in keys:
                    img_poly[:,:][img_boundary[:,:]==1] = artificial_class_label
            elif output_type == '3d':
                img_poly = cv2.fillPoly(img, pts=co_use_case, color=textline_rgb_color)
                if "artificial_class_label" in keys:
                    img_poly[:,:,0][img_boundary[:,:]==1] = artificial_class_rgb_color[0]
                    img_poly[:,:,1][img_boundary[:,:]==1] = artificial_class_rgb_color[1]
                    img_poly[:,:,2][img_boundary[:,:]==1] = artificial_class_rgb_color[2]

            try:
                cv2.imwrite(output_dir + '/' + gt_list[index].split('-')[1].split('.')[0] + '.png',
                            img_poly)
            except:
                cv2.imwrite(output_dir + '/' + gt_list[index].split('.')[0] + '.png', img_poly)

            
        if config_file and config_params['use_case']=='layout':
            keys = list(config_params.keys())
            if "artificial_class_on_boundry" in keys:
                elements_with_artificial_class = list(config_params['artificial_class_on_boundry'])
                artificial_class_rgb_color = (255,255,0)
                artificial_class_label = config_params['artificial_class_label']
            #values = config_params.values()

            if 'textregions' in keys:
                types_text_dict = config_params['textregions']
                types_text = list(types_text_dict.keys())
                types_text_label = list(types_text_dict.values())
                print(types_text)
            if 'graphicregions' in keys:
                types_graphic_dict = config_params['graphicregions']
                types_graphic = list(types_graphic_dict.keys())
                types_graphic_label = list(types_graphic_dict.values())

                
            labels_rgb_color = [ (0,0,0), (255,0,0), (255,125,0), (255,0,125), (125,255,125), (125,125,0), (0,125,255), (0,125,0), (125,125,125), (255,0,255), (125,0,125), (0,255,0),(0,0,255), (0,255,255), (255,125,125),  (0,125,125), (0,255,125), (255,125,255), (125,255,0)]
            
            region_tags=np.unique([x for x in alltags if x.endswith('Region')])   

            co_text_paragraph=[]
            co_text_footnote=[]
            co_text_footnote_con=[]
            co_text_drop=[]
            co_text_heading=[]
            co_text_header=[]
            co_text_marginalia=[]
            co_text_catch=[]
            co_text_page_number=[]
            co_text_signature_mark=[]
            co_sep=[]
            co_img=[]
            co_table=[]
            co_graphic_signature=[]
            co_graphic_text_annotation=[]
            co_graphic_decoration=[]
            co_graphic_stamp=[]
            co_noise=[]
            
            for tag in region_tags:
                if 'textregions' in keys:
                    if tag.endswith('}TextRegion') or tag.endswith('}Textregion'):
                        for nn in root1.iter(tag):
                            c_t_in_drop=[]
                            c_t_in_paragraph=[]
                            c_t_in_heading=[]
                            c_t_in_header=[]
                            c_t_in_page_number=[]
                            c_t_in_signature_mark=[]
                            c_t_in_catch=[]
                            c_t_in_marginalia=[]
                            c_t_in_footnote=[]
                            c_t_in_footnote_con=[]
                            sumi=0
                            for vv in nn.iter():
                                # check the format of coords
                                if vv.tag==link+'Coords':
                
                                    coords=bool(vv.attrib)
                                    if coords:
                                        #print('birda1')
                                        p_h=vv.attrib['points'].split(' ')
                                        
                                        if "drop-capital" in types_text:
                                            if "type" in nn.attrib and nn.attrib['type']=='drop-capital':
                                                c_t_in_drop.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                                
                                        if "footnote" in types_text:
                                            if "type" in nn.attrib and nn.attrib['type']=='footnote':
                                                c_t_in_footnote.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                                
                                        if "footnote-continued" in types_text:
                                            if "type" in nn.attrib and nn.attrib['type']=='footnote-continued':
                                                c_t_in_footnote_con.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                        
                                        if "heading" in types_text:
                                            if "type" in nn.attrib and nn.attrib['type']=='heading':
                                                c_t_in_heading.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                    
                                        if "signature-mark" in types_text:
                                            if "type" in nn.attrib and nn.attrib['type']=='signature-mark':
                                                c_t_in_signature_mark.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )

                                        if "header" in types_text:
                                            if "type" in nn.attrib and nn.attrib['type']=='header':
                                                c_t_in_header.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                        
                                        if "catch-word" in types_text:
                                            if "type" in nn.attrib and nn.attrib['type']=='catch-word':
                                                c_t_in_catch.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                    
                                        if "page-number" in types_text:
                                            if "type" in nn.attrib and nn.attrib['type']=='page-number':
                                                c_t_in_page_number.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )

                                        if "marginalia" in types_text:    
                                            if "type" in nn.attrib and nn.attrib['type']=='marginalia':
                                                c_t_in_marginalia.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                            
                                        if "paragraph" in types_text:
                                            if "type" in nn.attrib and nn.attrib['type']=='paragraph':
                                                c_t_in_paragraph.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )

                
                                        break
                                    else:
                                        pass
                
                
                                if vv.tag==link+'Point':
                                    if "drop-capital" in types_text:
                                        if "type" in nn.attrib and nn.attrib['type']=='drop-capital':
                                            c_t_in_drop.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                            sumi+=1
                                            
                                    if "footnote" in types_text:
                                        if "type" in nn.attrib and nn.attrib['type']=='footnote':
                                            c_t_in_footnote.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                            sumi+=1
                                        
                                    if "footnote-continued" in types_text:
                                        if "type" in nn.attrib and nn.attrib['type']=='footnote-continued':
                                            c_t_in_footnote_con.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                            sumi+=1
                                            
                                    if "heading" in types_text:
                                        if "type" in nn.attrib and nn.attrib['type']=='heading':
                                            c_t_in_heading.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                            sumi+=1
                                            
                                    if "signature-mark" in types_text:
                                        if "type" in nn.attrib and nn.attrib['type']=='signature-mark':
                                            c_t_in_signature_mark.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                            sumi+=1
                                        
                                    if "header" in types_text:
                                        if "type" in nn.attrib and nn.attrib['type']=='header':
                                            c_t_in_header.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                            sumi+=1
                                    
                                    if "catch-word" in types_text:
                                        if "type" in nn.attrib and nn.attrib['type']=='catch-word':
                                            c_t_in_catch.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                            sumi+=1
                                            
                                    if "page-number" in types_text:
                                        if "type" in nn.attrib and nn.attrib['type']=='page-number':
                                            c_t_in_page_number.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                            sumi+=1
                                    
                                    if "marginalia" in types_text:
                                        if "type" in nn.attrib and nn.attrib['type']=='marginalia':
                                            c_t_in_marginalia.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                            sumi+=1
                                        
                                    if "paragraph" in types_text:
                                        if "type" in nn.attrib and nn.attrib['type']=='paragraph':
                                            c_t_in_paragraph.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                            sumi+=1
                                        

                                elif vv.tag!=link+'Point' and sumi>=1:
                                    break
                
                            if len(c_t_in_drop)>0:
                                co_text_drop.append(np.array(c_t_in_drop))
                            if len(c_t_in_footnote_con)>0:
                                co_text_footnote_con.append(np.array(c_t_in_footnote_con))
                            if len(c_t_in_footnote)>0:
                                co_text_footnote.append(np.array(c_t_in_footnote))
                            if len(c_t_in_paragraph)>0:
                                co_text_paragraph.append(np.array(c_t_in_paragraph))
                            if len(c_t_in_heading)>0:
                                co_text_heading.append(np.array(c_t_in_heading))
                                
                            if len(c_t_in_header)>0:
                                co_text_header.append(np.array(c_t_in_header))
                            if len(c_t_in_page_number)>0:
                                co_text_page_number.append(np.array(c_t_in_page_number))
                            if len(c_t_in_catch)>0:
                                co_text_catch.append(np.array(c_t_in_catch))
                                
                            if len(c_t_in_signature_mark)>0:
                                co_text_signature_mark.append(np.array(c_t_in_signature_mark))
                                
                            if len(c_t_in_marginalia)>0:
                                co_text_marginalia.append(np.array(c_t_in_marginalia))
                                
                
                if 'graphicregions' in keys:
                    if tag.endswith('}GraphicRegion') or tag.endswith('}graphicregion'):
                        #print('sth')
                        for nn in root1.iter(tag):
                            c_t_in_stamp=[]
                            c_t_in_text_annotation=[]
                            c_t_in_decoration=[]
                            c_t_in_signature=[]
                            sumi=0
                            for vv in nn.iter():
                                # check the format of coords
                                if vv.tag==link+'Coords':
                                    coords=bool(vv.attrib)
                                    if coords:
                                        p_h=vv.attrib['points'].split(' ')
                                        if "handwritten-annotation" in types_graphic:
                                            if "type" in nn.attrib and nn.attrib['type']=='handwritten-annotation':
                                                c_t_in_text_annotation.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                        
                                        if "decoration" in types_graphic:
                                            if "type" in nn.attrib and nn.attrib['type']=='decoration':
                                                c_t_in_decoration.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )

                                        if "stamp" in types_graphic:
                                            if "type" in nn.attrib and nn.attrib['type']=='stamp':
                                                c_t_in_stamp.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                            
                                        if "signature" in types_graphic:
                                            if "type" in nn.attrib and nn.attrib['type']=='signature':
                                                c_t_in_signature.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                    
                                        
                                        
                                        break
                                    else:
                                        pass
                
                
                                if vv.tag==link+'Point':
                                    if "handwritten-annotation" in types_graphic:
                                        if "type" in nn.attrib and nn.attrib['type']=='handwritten-annotation':
                                            c_t_in_text_annotation.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                            sumi+=1
                                            
                                    if "decoration" in types_graphic:        
                                        if "type" in nn.attrib and nn.attrib['type']=='decoration':
                                            c_t_in_decoration.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                            sumi+=1
                                        
                                    if "stamp" in types_graphic:
                                        if "type" in nn.attrib and nn.attrib['type']=='stamp':
                                            c_t_in_stamp.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                            sumi+=1
                                        
                                    if "signature" in types_graphic:
                                        if "type" in nn.attrib and nn.attrib['type']=='signature':
                                            c_t_in_signature.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                            sumi+=1
                                    
                            if len(c_t_in_text_annotation)>0:
                                co_graphic_text_annotation.append(np.array(c_t_in_text_annotation))
                            if len(c_t_in_decoration)>0:
                                co_graphic_decoration.append(np.array(c_t_in_decoration))
                            if len(c_t_in_stamp)>0:
                                co_graphic_stamp.append(np.array(c_t_in_stamp))
                            if len(c_t_in_signature)>0:
                                co_graphic_signature.append(np.array(c_t_in_signature))
            
                if 'imageregion' in keys:
                    if tag.endswith('}ImageRegion') or tag.endswith('}imageregion'):
                        for nn in root1.iter(tag):
                            c_t_in=[]
                            sumi=0
                            for vv in nn.iter():
                                if vv.tag==link+'Coords':
                                    coords=bool(vv.attrib)
                                    if coords:
                                        p_h=vv.attrib['points'].split(' ')
                                        c_t_in.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                        break
                                    else:
                                        pass
                
                
                                if vv.tag==link+'Point':
                                    c_t_in.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                    sumi+=1

                                elif vv.tag!=link+'Point' and sumi>=1:
                                    break
                            co_img.append(np.array(c_t_in))
            
                
                if 'separatorregion' in keys:
                    if tag.endswith('}SeparatorRegion') or tag.endswith('}separatorregion'):
                        for nn in root1.iter(tag):
                            c_t_in=[]
                            sumi=0
                            for vv in nn.iter():
                                # check the format of coords
                                if vv.tag==link+'Coords':
                                    coords=bool(vv.attrib)
                                    if coords:
                                        p_h=vv.attrib['points'].split(' ')
                                        c_t_in.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                        break
                                    else:
                                        pass
                
                
                                if vv.tag==link+'Point':
                                    c_t_in.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                    sumi+=1

                                elif vv.tag!=link+'Point' and sumi>=1:
                                    break
                            co_sep.append(np.array(c_t_in))
            
            
            
                if 'tableregion' in keys:
                    if tag.endswith('}TableRegion') or tag.endswith('}tableregion'):
                        #print('sth')
                        for nn in root1.iter(tag):
                            c_t_in=[]
                            sumi=0
                            for vv in nn.iter():
                                # check the format of coords
                                if vv.tag==link+'Coords':
                                    coords=bool(vv.attrib)
                                    if coords:
                                        p_h=vv.attrib['points'].split(' ')
                                        c_t_in.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                        break
                                    else:
                                        pass
                
                
                                if vv.tag==link+'Point':
                                    c_t_in.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                    sumi+=1
                                #print(vv.tag,'in')
                                elif vv.tag!=link+'Point' and sumi>=1:
                                    break
                            co_table.append(np.array(c_t_in))
            
                if 'noiseregion' in keys:
                    if tag.endswith('}NoiseRegion') or tag.endswith('}noiseregion'):
                        #print('sth')
                        for nn in root1.iter(tag):
                            c_t_in=[]
                            sumi=0
                            for vv in nn.iter():
                                # check the format of coords
                                if vv.tag==link+'Coords':
                                    coords=bool(vv.attrib)
                                    if coords:
                                        p_h=vv.attrib['points'].split(' ')
                                        c_t_in.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                        break
                                    else:
                                        pass
                
                
                                if vv.tag==link+'Point':
                                    c_t_in.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                                    sumi+=1
                                #print(vv.tag,'in')
                                elif vv.tag!=link+'Point' and sumi>=1:
                                    break
                            co_noise.append(np.array(c_t_in))
            
            if "artificial_class_on_boundry" in keys:
                img_boundary = np.zeros( (y_len,x_len) )
                if "paragraph" in elements_with_artificial_class:
                    erosion_rate = 2
                    dilation_rate = 4
                    co_text_paragraph, img_boundary = update_region_contours(co_text_paragraph, img_boundary, erosion_rate, dilation_rate, y_len, x_len )
                if "drop-capital" in elements_with_artificial_class:
                    erosion_rate = 0
                    dilation_rate = 4
                    co_text_drop, img_boundary = update_region_contours(co_text_drop, img_boundary, erosion_rate, dilation_rate, y_len, x_len )
                if "catch-word" in elements_with_artificial_class:
                    erosion_rate = 0
                    dilation_rate = 4
                    co_text_catch, img_boundary = update_region_contours(co_text_catch, img_boundary, erosion_rate, dilation_rate, y_len, x_len )
                if "page-number" in elements_with_artificial_class:
                    erosion_rate = 0
                    dilation_rate = 4
                    co_text_page_number, img_boundary = update_region_contours(co_text_page_number, img_boundary, erosion_rate, dilation_rate, y_len, x_len )
                if "header" in elements_with_artificial_class:
                    erosion_rate = 1
                    dilation_rate = 4
                    co_text_header, img_boundary = update_region_contours(co_text_header, img_boundary, erosion_rate, dilation_rate, y_len, x_len )
                if "heading" in elements_with_artificial_class:
                    erosion_rate = 1
                    dilation_rate = 4
                    co_text_heading, img_boundary = update_region_contours(co_text_heading, img_boundary, erosion_rate, dilation_rate, y_len, x_len )
                if "signature-mark" in elements_with_artificial_class:
                    erosion_rate = 1
                    dilation_rate = 4
                    co_text_signature_mark, img_boundary = update_region_contours(co_text_signature_mark, img_boundary, erosion_rate, dilation_rate, y_len, x_len )
                if "marginalia" in elements_with_artificial_class:
                    erosion_rate = 2
                    dilation_rate = 4
                    co_text_marginalia, img_boundary = update_region_contours(co_text_marginalia, img_boundary, erosion_rate, dilation_rate, y_len, x_len )
                if "footnote" in elements_with_artificial_class:
                    erosion_rate = 2
                    dilation_rate = 4
                    co_text_footnote, img_boundary = update_region_contours(co_text_footnote, img_boundary, erosion_rate, dilation_rate, y_len, x_len )
                if "footnote-continued" in elements_with_artificial_class:
                    erosion_rate = 2
                    dilation_rate = 4
                    co_text_footnote_con, img_boundary = update_region_contours(co_text_footnote_con, img_boundary, erosion_rate, dilation_rate, y_len, x_len )
                    
                    
                
            img = np.zeros( (y_len,x_len,3) ) 

            if output_type == '3d':
                
                if 'graphicregions' in keys:
                    if "handwritten-annotation" in types_graphic:
                        img_poly=cv2.fillPoly(img, pts =co_graphic_text_annotation, color=labels_rgb_color[ config_params['graphicregions']['handwritten-annotation']])
                    if "signature" in types_graphic:
                        img_poly=cv2.fillPoly(img, pts =co_graphic_signature, color=labels_rgb_color[ config_params['graphicregions']['signature']])
                    if "decoration" in types_graphic:
                        img_poly=cv2.fillPoly(img, pts =co_graphic_decoration, color=labels_rgb_color[ config_params['graphicregions']['decoration']])
                    if "stamp" in types_graphic:
                        img_poly=cv2.fillPoly(img, pts =co_graphic_stamp, color=labels_rgb_color[ config_params['graphicregions']['stamp']])
                        
                if 'imageregion' in keys: 
                    img_poly=cv2.fillPoly(img, pts =co_img, color=labels_rgb_color[ config_params['imageregion']])
                if 'separatorregion' in keys: 
                    img_poly=cv2.fillPoly(img, pts =co_sep, color=labels_rgb_color[ config_params['separatorregion']])
                if 'tableregion' in keys:  
                    img_poly=cv2.fillPoly(img, pts =co_table, color=labels_rgb_color[ config_params['tableregion']])
                if 'noiseregion' in keys:  
                    img_poly=cv2.fillPoly(img, pts =co_noise, color=labels_rgb_color[ config_params['noiseregion']])
                    
                if 'textregions' in keys:
                    if "paragraph" in types_text:
                        img_poly=cv2.fillPoly(img, pts =co_text_paragraph, color=labels_rgb_color[ config_params['textregions']['paragraph']])
                    if "footnote" in types_text:
                        img_poly=cv2.fillPoly(img, pts =co_text_footnote, color=labels_rgb_color[ config_params['textregions']['footnote']])
                    if "footnote-continued" in types_text:
                        img_poly=cv2.fillPoly(img, pts =co_text_footnote_con, color=labels_rgb_color[ config_params['textregions']['footnote-continued']])
                    if "heading" in types_text:
                        img_poly=cv2.fillPoly(img, pts =co_text_heading, color=labels_rgb_color[ config_params['textregions']['heading']])
                    if "header" in types_text:
                        img_poly=cv2.fillPoly(img, pts =co_text_header, color=labels_rgb_color[ config_params['textregions']['header']])
                    if "catch-word" in types_text:
                        img_poly=cv2.fillPoly(img, pts =co_text_catch, color=labels_rgb_color[ config_params['textregions']['catch-word']])
                    if "signature-mark" in types_text:
                        img_poly=cv2.fillPoly(img, pts =co_text_signature_mark, color=labels_rgb_color[ config_params['textregions']['signature-mark']])
                    if "page-number" in types_text:
                        img_poly=cv2.fillPoly(img, pts =co_text_page_number, color=labels_rgb_color[ config_params['textregions']['page-number']])
                    if "marginalia" in types_text:
                        img_poly=cv2.fillPoly(img, pts =co_text_marginalia, color=labels_rgb_color[ config_params['textregions']['marginalia']])
                    if "drop-capital" in types_text:
                        img_poly=cv2.fillPoly(img, pts =co_text_drop, color=labels_rgb_color[ config_params['textregions']['drop-capital']])
                        
                if "artificial_class_on_boundry" in keys:
                    img_poly[:,:,0][img_boundary[:,:]==1] = artificial_class_rgb_color[0]
                    img_poly[:,:,1][img_boundary[:,:]==1] = artificial_class_rgb_color[1]
                    img_poly[:,:,2][img_boundary[:,:]==1] = artificial_class_rgb_color[2]
                    

                    
                
            elif output_type == '2d':
                if 'graphicregions' in keys:
                    if "handwritten-annotation" in types_graphic:
                        color_label = config_params['graphicregions']['handwritten-annotation']
                        img_poly=cv2.fillPoly(img, pts =co_graphic_text_annotation, color=(color_label,color_label,color_label))
                    if "signature" in types_graphic:
                        color_label = config_params['graphicregions']['signature']
                        img_poly=cv2.fillPoly(img, pts =co_graphic_signature, color=(color_label,color_label,color_label))
                    if "decoration" in types_graphic:
                        color_label = config_params['graphicregions']['decoration']
                        img_poly=cv2.fillPoly(img, pts =co_graphic_decoration, color=(color_label,color_label,color_label))
                    if "stamp" in types_graphic:
                        color_label = config_params['graphicregions']['stamp']
                        img_poly=cv2.fillPoly(img, pts =co_graphic_stamp, color=(color_label,color_label,color_label))
                
                if 'imageregion' in keys:
                    color_label = config_params['imageregion']
                    img_poly=cv2.fillPoly(img, pts =co_img, color=(color_label,color_label,color_label))
                if 'separatorregion' in keys: 
                    color_label = config_params['separatorregion']
                    img_poly=cv2.fillPoly(img, pts =co_sep, color=(color_label,color_label,color_label))
                if 'tableregion' in keys:
                    color_label = config_params['tableregion']
                    img_poly=cv2.fillPoly(img, pts =co_table, color=(color_label,color_label,color_label))
                if 'noiseregion' in keys:
                    color_label = config_params['noiseregion']
                    img_poly=cv2.fillPoly(img, pts =co_noise, color=(color_label,color_label,color_label))
                    
                if 'textregions' in keys:
                    if "paragraph" in types_text:
                        color_label = config_params['textregions']['paragraph']
                        img_poly=cv2.fillPoly(img, pts =co_text_paragraph, color=(color_label,color_label,color_label))
                    if "footnote" in types_text:
                        color_label = config_params['textregions']['footnote']
                        img_poly=cv2.fillPoly(img, pts =co_text_footnote, color=(color_label,color_label,color_label))
                    if "footnote-continued" in types_text:
                        color_label = config_params['textregions']['footnote-continued']
                        img_poly=cv2.fillPoly(img, pts =co_text_footnote_con, color=(color_label,color_label,color_label))
                    if "heading" in types_text:
                        color_label = config_params['textregions']['heading']
                        img_poly=cv2.fillPoly(img, pts =co_text_heading, color=(color_label,color_label,color_label))
                    if "header" in types_text:
                        color_label = config_params['textregions']['header']
                        img_poly=cv2.fillPoly(img, pts =co_text_header, color=(color_label,color_label,color_label))
                    if "catch-word" in types_text:
                        color_label = config_params['textregions']['catch-word']
                        img_poly=cv2.fillPoly(img, pts =co_text_catch, color=(color_label,color_label,color_label))
                    if "signature-mark" in types_text:
                        color_label = config_params['textregions']['signature-mark']
                        img_poly=cv2.fillPoly(img, pts =co_text_signature_mark, color=(color_label,color_label,color_label))
                    if "page-number" in types_text:
                        color_label = config_params['textregions']['page-number']
                        img_poly=cv2.fillPoly(img, pts =co_text_page_number, color=(color_label,color_label,color_label))
                    if "marginalia" in types_text:
                        color_label = config_params['textregions']['marginalia']
                        img_poly=cv2.fillPoly(img, pts =co_text_marginalia, color=(color_label,color_label,color_label))
                    if "drop-capital" in types_text:
                        color_label = config_params['textregions']['drop-capital']
                        img_poly=cv2.fillPoly(img, pts =co_text_drop, color=(color_label,color_label,color_label))
                        
                if "artificial_class_on_boundry" in keys:
                    img_poly[:,:][img_boundary[:,:]==1] = artificial_class_label
                
                
                
                
            try: 
                cv2.imwrite(output_dir+'/'+gt_list[index].split('-')[1].split('.')[0]+'.png',img_poly )
            except:
                cv2.imwrite(output_dir+'/'+gt_list[index].split('.')[0]+'.png',img_poly )
                
                
                
def find_new_features_of_contours(contours_main):
    
    #print(contours_main[0][0][:, 0])

    areas_main = np.array([cv2.contourArea(contours_main[j]) for j in range(len(contours_main))])
    M_main = [cv2.moments(contours_main[j]) for j in range(len(contours_main))]
    cx_main = [(M_main[j]["m10"] / (M_main[j]["m00"] + 1e-32)) for j in range(len(M_main))]
    cy_main = [(M_main[j]["m01"] / (M_main[j]["m00"] + 1e-32)) for j in range(len(M_main))]
    try:
        x_min_main = np.array([np.min(contours_main[j][0][:, 0]) for j in range(len(contours_main))])

        argmin_x_main = np.array([np.argmin(contours_main[j][0][:, 0]) for j in range(len(contours_main))])

        x_min_from_argmin = np.array([contours_main[j][0][argmin_x_main[j], 0] for j in range(len(contours_main))])
        y_corr_x_min_from_argmin = np.array([contours_main[j][0][argmin_x_main[j], 1] for j in range(len(contours_main))])

        x_max_main = np.array([np.max(contours_main[j][0][:, 0]) for j in range(len(contours_main))])

        y_min_main = np.array([np.min(contours_main[j][0][:, 1]) for j in range(len(contours_main))])
        y_max_main = np.array([np.max(contours_main[j][0][:, 1]) for j in range(len(contours_main))])
    except:
        x_min_main = np.array([np.min(contours_main[j][:, 0]) for j in range(len(contours_main))])

        argmin_x_main = np.array([np.argmin(contours_main[j][:, 0]) for j in range(len(contours_main))])

        x_min_from_argmin = np.array([contours_main[j][argmin_x_main[j], 0] for j in range(len(contours_main))])
        y_corr_x_min_from_argmin = np.array([contours_main[j][argmin_x_main[j], 1] for j in range(len(contours_main))])

        x_max_main = np.array([np.max(contours_main[j][:, 0]) for j in range(len(contours_main))])

        y_min_main = np.array([np.min(contours_main[j][:, 1]) for j in range(len(contours_main))])
        y_max_main = np.array([np.max(contours_main[j][:, 1]) for j in range(len(contours_main))])

    # dis_x=np.abs(x_max_main-x_min_main)

    return cx_main, cy_main, x_min_main, x_max_main, y_min_main, y_max_main, y_corr_x_min_from_argmin
def read_xml(xml_file):
    file_name = Path(xml_file).stem
    tree1 = ET.parse(xml_file)
    root1=tree1.getroot()
    alltags=[elem.tag for elem in root1.iter()]
    link=alltags[0].split('}')[0]+'}'

    index_tot_regions = []
    tot_region_ref = []

    for jj in root1.iter(link+'Page'):
        y_len=int(jj.attrib['imageHeight'])
        x_len=int(jj.attrib['imageWidth'])


    for jj in root1.iter(link+'RegionRefIndexed'):
        index_tot_regions.append(jj.attrib['index'])
        tot_region_ref.append(jj.attrib['regionRef'])

    region_tags=np.unique([x for x in alltags if x.endswith('Region')])   
    #print(region_tags)
    co_text_paragraph=[]
    co_text_drop=[]
    co_text_heading=[]
    co_text_header=[]
    co_text_marginalia=[]
    co_text_catch=[]
    co_text_page_number=[]
    co_text_signature_mark=[]
    co_sep=[]
    co_img=[]
    co_table=[]
    co_graphic=[]
    co_graphic_text_annotation=[]
    co_graphic_decoration=[]
    co_noise=[]


    co_text_paragraph_text=[]
    co_text_drop_text=[]
    co_text_heading_text=[]
    co_text_header_text=[]
    co_text_marginalia_text=[]
    co_text_catch_text=[]
    co_text_page_number_text=[]
    co_text_signature_mark_text=[]
    co_sep_text=[]
    co_img_text=[]
    co_table_text=[]
    co_graphic_text=[]
    co_graphic_text_annotation_text=[]
    co_graphic_decoration_text=[]
    co_noise_text=[]


    id_paragraph = []
    id_header = []
    id_heading = []
    id_marginalia = []

    for tag in region_tags:
        if tag.endswith('}TextRegion') or tag.endswith('}Textregion'):
            for nn in root1.iter(tag):
                for child2 in nn:
                    tag2 = child2.tag
                    #print(child2.tag)
                    if tag2.endswith('}TextEquiv') or tag2.endswith('}TextEquiv'):
                        #children2 = childtext.getchildren()
                        #rank = child2.find('Unicode').text
                        for childtext2 in child2:
                            #rank = childtext2.find('Unicode').text
                            #if childtext2.tag.endswith('}PlainText') or childtext2.tag.endswith('}PlainText'):
                            #print(childtext2.text)
                            if childtext2.tag.endswith('}Unicode') or childtext2.tag.endswith('}Unicode'):
                                if "type" in nn.attrib and nn.attrib['type']=='drop-capital':
                                    co_text_drop_text.append(childtext2.text)
                                elif "type" in nn.attrib and nn.attrib['type']=='heading':
                                    co_text_heading_text.append(childtext2.text)
                                elif "type" in nn.attrib and nn.attrib['type']=='signature-mark':
                                    co_text_signature_mark_text.append(childtext2.text)
                                elif "type" in nn.attrib and nn.attrib['type']=='header':
                                    co_text_header_text.append(childtext2.text)
                                elif "type" in nn.attrib and nn.attrib['type']=='catch-word':
                                    co_text_catch_text.append(childtext2.text)
                                elif "type" in nn.attrib and nn.attrib['type']=='page-number':
                                    co_text_page_number_text.append(childtext2.text)
                                elif "type" in nn.attrib and nn.attrib['type']=='marginalia':
                                    co_text_marginalia_text.append(childtext2.text)
                                else:
                                    co_text_paragraph_text.append(childtext2.text)
                c_t_in_drop=[]
                c_t_in_paragraph=[]
                c_t_in_heading=[]
                c_t_in_header=[]
                c_t_in_page_number=[]
                c_t_in_signature_mark=[]
                c_t_in_catch=[]
                c_t_in_marginalia=[]


                sumi=0
                for vv in nn.iter():
                    # check the format of coords
                    if vv.tag==link+'Coords':

                        coords=bool(vv.attrib)
                        if coords:
                            #print('birda1')
                            p_h=vv.attrib['points'].split(' ')



                            if "type" in nn.attrib and nn.attrib['type']=='drop-capital':
                            #if nn.attrib['type']=='paragraph':

                                c_t_in_drop.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )

                            elif "type" in nn.attrib and nn.attrib['type']=='heading':
                                id_heading.append(nn.attrib['id'])
                                c_t_in_heading.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )


                            elif "type" in nn.attrib and nn.attrib['type']=='signature-mark':

                                c_t_in_signature_mark.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                #print(c_t_in_paragraph)
                            elif "type" in nn.attrib and nn.attrib['type']=='header':
                                id_header.append(nn.attrib['id'])
                                c_t_in_header.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )


                            elif "type" in nn.attrib and nn.attrib['type']=='catch-word':
                                c_t_in_catch.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )


                            elif "type" in nn.attrib and nn.attrib['type']=='page-number':

                                c_t_in_page_number.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                #print(c_t_in_paragraph)

                            elif "type" in nn.attrib and nn.attrib['type']=='marginalia':
                                id_marginalia.append(nn.attrib['id'])

                                c_t_in_marginalia.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                #print(c_t_in_paragraph)
                            else:
                                #print(nn.attrib['id'])

                                id_paragraph.append(nn.attrib['id'])

                                c_t_in_paragraph.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                #print(c_t_in_paragraph)

                            break
                        else:
                            pass


                    if vv.tag==link+'Point':
                        if "type" in nn.attrib and nn.attrib['type']=='drop-capital':
                        #if nn.attrib['type']=='paragraph':

                            c_t_in_drop.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                            sumi+=1

                        elif "type" in nn.attrib and nn.attrib['type']=='heading':
                            id_heading.append(nn.attrib['id'])
                            c_t_in_heading.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                            sumi+=1


                        elif "type" in nn.attrib and nn.attrib['type']=='signature-mark':

                            c_t_in_signature_mark.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                            #print(c_t_in_paragraph)
                            sumi+=1
                        elif "type" in nn.attrib and nn.attrib['type']=='header':
                            id_header.append(nn.attrib['id'])
                            c_t_in_header.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                            sumi+=1


                        elif "type" in nn.attrib and nn.attrib['type']=='catch-word':
                            c_t_in_catch.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                            sumi+=1


                        elif "type" in nn.attrib and nn.attrib['type']=='page-number':

                            c_t_in_page_number.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                            #print(c_t_in_paragraph)
                            sumi+=1

                        elif "type" in nn.attrib and nn.attrib['type']=='marginalia':
                            id_marginalia.append(nn.attrib['id'])

                            c_t_in_marginalia.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                            #print(c_t_in_paragraph)
                            sumi+=1

                        else:
                            id_paragraph.append(nn.attrib['id'])
                            c_t_in_paragraph.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                            #print(c_t_in_paragraph)
                            sumi+=1

                        #c_t_in.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])

                    #print(vv.tag,'in')
                    elif vv.tag!=link+'Point' and sumi>=1:
                        break

                if len(c_t_in_drop)>0:
                    co_text_drop.append(np.array(c_t_in_drop))
                if len(c_t_in_paragraph)>0:
                    co_text_paragraph.append(np.array(c_t_in_paragraph))
                if len(c_t_in_heading)>0:
                    co_text_heading.append(np.array(c_t_in_heading))

                if len(c_t_in_header)>0:
                    co_text_header.append(np.array(c_t_in_header))
                if len(c_t_in_page_number)>0:
                    co_text_page_number.append(np.array(c_t_in_page_number))
                if len(c_t_in_catch)>0:
                    co_text_catch.append(np.array(c_t_in_catch))

                if len(c_t_in_signature_mark)>0:
                    co_text_signature_mark.append(np.array(c_t_in_signature_mark))

                if len(c_t_in_marginalia)>0:
                    co_text_marginalia.append(np.array(c_t_in_marginalia))


        elif tag.endswith('}GraphicRegion') or tag.endswith('}graphicregion'):
            #print('sth')
            for nn in root1.iter(tag):
                c_t_in=[]
                c_t_in_text_annotation=[]
                c_t_in_decoration=[]
                sumi=0
                for vv in nn.iter():
                    # check the format of coords
                    if vv.tag==link+'Coords':
                        coords=bool(vv.attrib)
                        if coords:
                            p_h=vv.attrib['points'].split(' ')
                            #c_t_in.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )

                            if "type" in nn.attrib and nn.attrib['type']=='handwritten-annotation':
                            #if nn.attrib['type']=='paragraph':

                                c_t_in_text_annotation.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )

                            elif "type" in nn.attrib and nn.attrib['type']=='decoration':

                                c_t_in_decoration.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                                #print(c_t_in_paragraph)
                            else:
                                c_t_in.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )



                            break
                        else:
                            pass


                    if vv.tag==link+'Point':

                        if "type" in nn.attrib and nn.attrib['type']=='handwritten-annotation':
                        #if nn.attrib['type']=='paragraph':

                            c_t_in_text_annotation.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                            sumi+=1

                        elif "type" in nn.attrib and nn.attrib['type']=='decoration':

                            c_t_in_decoration.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                            #print(c_t_in_paragraph)
                            sumi+=1
                        else:
                            c_t_in.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                            sumi+=1

                if len(c_t_in_text_annotation)>0:
                    co_graphic_text_annotation.append(np.array(c_t_in_text_annotation))
                if len(c_t_in_decoration)>0:
                    co_graphic_decoration.append(np.array(c_t_in_decoration))
                if len(c_t_in)>0:
                    co_graphic.append(np.array(c_t_in))



        elif tag.endswith('}ImageRegion') or tag.endswith('}imageregion'):
            #print('sth')
            for nn in root1.iter(tag):
                c_t_in=[]
                sumi=0
                for vv in nn.iter():
                    # check the format of coords
                    if vv.tag==link+'Coords':
                        coords=bool(vv.attrib)
                        if coords:
                            p_h=vv.attrib['points'].split(' ')
                            c_t_in.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                            break
                        else:
                            pass


                    if vv.tag==link+'Point':
                        c_t_in.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                        sumi+=1
                    #print(vv.tag,'in')
                    elif vv.tag!=link+'Point' and sumi>=1:
                        break
                co_img.append(np.array(c_t_in))
                co_img_text.append(' ')


        elif tag.endswith('}SeparatorRegion') or tag.endswith('}separatorregion'):
            #print('sth')
            for nn in root1.iter(tag):
                c_t_in=[]
                sumi=0
                for vv in nn.iter():
                    # check the format of coords
                    if vv.tag==link+'Coords':
                        coords=bool(vv.attrib)
                        if coords:
                            p_h=vv.attrib['points'].split(' ')
                            c_t_in.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                            break
                        else:
                            pass


                    if vv.tag==link+'Point':
                        c_t_in.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                        sumi+=1
                    #print(vv.tag,'in')
                    elif vv.tag!=link+'Point' and sumi>=1:
                        break
                co_sep.append(np.array(c_t_in))



        elif tag.endswith('}TableRegion') or tag.endswith('}tableregion'):
            #print('sth')
            for nn in root1.iter(tag):
                c_t_in=[]
                sumi=0
                for vv in nn.iter():
                    # check the format of coords
                    if vv.tag==link+'Coords':
                        coords=bool(vv.attrib)
                        if coords:
                            p_h=vv.attrib['points'].split(' ')
                            c_t_in.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                            break
                        else:
                            pass


                    if vv.tag==link+'Point':
                        c_t_in.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                        sumi+=1
                    #print(vv.tag,'in')
                    elif vv.tag!=link+'Point' and sumi>=1:
                        break
                co_table.append(np.array(c_t_in))
                co_table_text.append(' ')

        elif tag.endswith('}NoiseRegion') or tag.endswith('}noiseregion'):
            #print('sth')
            for nn in root1.iter(tag):
                c_t_in=[]
                sumi=0
                for vv in nn.iter():
                    # check the format of coords
                    if vv.tag==link+'Coords':
                        coords=bool(vv.attrib)
                        if coords:
                            p_h=vv.attrib['points'].split(' ')
                            c_t_in.append( np.array( [ [ int(x.split(',')[0]) , int(x.split(',')[1]) ]  for x in p_h] ) )
                            break
                        else:
                            pass


                    if vv.tag==link+'Point':
                        c_t_in.append([ int(np.float(vv.attrib['x'])) , int(np.float(vv.attrib['y'])) ])
                        sumi+=1
                    #print(vv.tag,'in')
                    elif vv.tag!=link+'Point' and sumi>=1:
                        break
                co_noise.append(np.array(c_t_in))
                co_noise_text.append(' ')


    img = np.zeros( (y_len,x_len,3) ) 

    img_poly=cv2.fillPoly(img, pts =co_text_paragraph, color=(1,1,1))

    img_poly=cv2.fillPoly(img, pts =co_text_heading, color=(2,2,2))
    img_poly=cv2.fillPoly(img, pts =co_text_header, color=(2,2,2))
    #img_poly=cv2.fillPoly(img, pts =co_text_catch, color=(125,255,125))
    #img_poly=cv2.fillPoly(img, pts =co_text_signature_mark, color=(125,125,0))
    #img_poly=cv2.fillPoly(img, pts =co_graphic_decoration, color=(1,125,255))
    #img_poly=cv2.fillPoly(img, pts =co_text_page_number, color=(1,125,0))
    img_poly=cv2.fillPoly(img, pts =co_text_marginalia, color=(3,3,3))
    #img_poly=cv2.fillPoly(img, pts =co_text_drop, color=(1,125,255))

    #img_poly=cv2.fillPoly(img, pts =co_graphic_text_annotation, color=(125,0,125))
    img_poly=cv2.fillPoly(img, pts =co_img, color=(4,4,4))
    img_poly=cv2.fillPoly(img, pts =co_sep, color=(5,5,5))
    #img_poly=cv2.fillPoly(img, pts =co_table, color=(1,255,255))
    #img_poly=cv2.fillPoly(img, pts =co_graphic, color=(255,125,125))
    #img_poly=cv2.fillPoly(img, pts =co_noise, color=(255,0,255))

    #print('yazdimmm',self.output_dir+'/'+self.gt_list[index].split('.')[0]+'.jpg')
    ###try: 
        ####print('yazdimmm',self.output_dir+'/'+self.gt_list[index].split('.')[0]+'.jpg')
        ###cv2.imwrite(self.output_dir+'/'+self.gt_list[index].split('-')[1].split('.')[0]+'.jpg',img_poly )
    ###except:
        ###cv2.imwrite(self.output_dir+'/'+self.gt_list[index].split('.')[0]+'.jpg',img_poly )
    return file_name, id_paragraph, id_header,co_text_paragraph, co_text_header,\
tot_region_ref,x_len, y_len,index_tot_regions, img_poly




def bounding_box(cnt,color, corr_order_index ):
    x, y, w, h = cv2.boundingRect(cnt)
    x = int(x*scale_w)
    y = int(y*scale_h)
    
    w = int(w*scale_w)
    h = int(h*scale_h)
    
    return [x,y,w,h,int(color), int(corr_order_index)+1]

def resize_image(seg_in,input_height,input_width):
    return cv2.resize(seg_in,(input_width,input_height),interpolation=cv2.INTER_NEAREST)

def make_image_from_bb(width_l, height_l, bb_all):
    bb_all =np.array(bb_all)
    img_remade = np.zeros((height_l,width_l ))
    
    for i in range(bb_all.shape[0]):
        img_remade[bb_all[i,1]:bb_all[i,1]+bb_all[i,3],bb_all[i,0]:bb_all[i,0]+bb_all[i,2] ] = 1
    return img_remade