import numpy as np
import cv2
import imutils
from skimage import exposure
from pytesseract import image_to_string, image_to_boxes
import PIL

def take_picture(should_save=False, d_id=0):
  cam = cv2.VideoCapture(d_id)
  s, img = cam.read()
  if s:
    if should_save:
      cv2.imwrite('ocr.jpg',img)
  return img

def cnvt_edged_image(img_arr, should_save=False):
  ratio = img_arr.shape[0] / 300.0
  image = imutils.resize(img_arr,height=300)
  gray_image = cv2.bilateralFilter(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY),11, 17, 17)
  edged_image = cv2.Canny(gray_image, 30, 200)

  if should_save:
    cv2.imwrite('cntr_ocr.jpg')

  return edged_image

'''image passed in must be ran through the cnv_edge_image first'''
def find_display_contour(edge_img_arr):
  display_contour = None
  edge_copy = edge_img_arr.copy()
  contours,hierarchy = cv2.findContours(edge_copy, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
  top_cntrs = sorted(contours, key = cv2.contourArea, reverse = True)[:10]

  for cntr in top_cntrs:
    peri = cv2.arcLength(cntr,True)
    approx = cv2.approxPolyDP(cntr, 0.02 * peri, True)

    if len(approx) == 4:
      display_contour = approx
      break

  return display_contour

def crop_display(image_arr):
  if crop == True:
    edge_image = cnvt_edged_image(image_arr)
    display_contour = find_display_contour(edge_image)
    cntr_pts = display_contour.reshape(4,2)
    return cntr_pts


def normalize_contrs(img,cntr_pts):
  ratio = img.shape[0] / 300.0
  norm_pts = np.zeros((4,2), dtype="float32")

  s = cntr_pts.sum(axis=1)
  norm_pts[0] = cntr_pts[np.argmin(s)]
  norm_pts[2] = cntr_pts[np.argmax(s)]

  d = np.diff(cntr_pts,axis=1)
  norm_pts[1] = cntr_pts[np.argmin(d)]
  norm_pts[3] = cntr_pts[np.argmax(d)]

  norm_pts *= ratio

  (top_left, top_right, bottom_right, bottom_left) = norm_pts

  width1 = np.sqrt(((bottom_right[0] - bottom_left[0]) ** 2) + ((bottom_right[1] - bottom_left[1]) ** 2))
  width2 = np.sqrt(((top_right[0] - top_left[0]) ** 2) + ((top_right[1] - top_left[1]) ** 2))
  height1 = np.sqrt(((top_right[0] - bottom_right[0]) ** 2) + ((top_right[1] - bottom_right[1]) ** 2))
  height2 = np.sqrt(((top_left[0] - bottom_left[0]) ** 2) + ((top_left[1] - bottom_left[1]) ** 2))

  max_width = max(int(width1), int(width2))
  max_height = max(int(height1), int(height2))

  dst = np.array([[0,0], [max_width -1, 0],[max_width -1, max_height -1],[0, max_height-1]], dtype="float32")
  persp_matrix = cv2.getPerspectiveTransform(norm_pts,dst)
  return cv2.warpPerspective(img,persp_matrix,(max_width,max_height))

def process_image(orig_image_arr):
  ratio = orig_image_arr.shape[0] / 300.0
  if crop ==True:
    display_image_arr = normalize_contrs(orig_image_arr,crop_display(orig_image_arr))
  #display image is now segmented.
  else:
    display_image_arr=orig_image_arr
  
  gry_disp_arr = cv2.cvtColor(display_image_arr, cv2.COLOR_BGR2GRAY)
  gry_disp_arr = cv2.blur(gry_disp_arr, (3, 4))
  gry_disp_arr = cv2.addWeighted(gry_disp_arr, 1.5, gry_disp_arr, 0, 1)
  gry_disp_arr = exposure.rescale_intensity(gry_disp_arr, out_range= (0,255))

  #thresholding
  ret, thresh = cv2.threshold(gry_disp_arr,127,255,cv2.THRESH_BINARY)
  return thresh

def ocr_image(orig_image_arr):
  orig_image_arr=process_image(orig_image_arr)
  otsu_thresh_image=PIL.Image.fromarray(orig_image_arr)
  otsu_thresh_image=otsu_thresh_image.convert('RGB')
  img=otsu_thresh_image
  
  output= image_to_string(img, lang="letsgodigital", config="--psm 12 -c tessedit_char_whitelist=.0123456789")
  return output

def ocr_image_boxed(orig_image):
  orig_image_arr=process_image(orig_image)
  cv2.imshow('img processed', orig_image_arr)
  otsu_thresh_image=PIL.Image.fromarray(orig_image_arr)
  otsu_thresh_image=otsu_thresh_image.convert('RGB')
  img=otsu_thresh_image
  print(type(otsu_thresh_image))
  
  img=np.array(img)
  hImg, wImg, _= img.shape
  boxes= image_to_boxes(img, lang="letsgodigital", config="--psm 7 -c tessedit_char_whitelist=.0123456789")
  
  for b in boxes.splitlines():
    b = b.split(' ')
    #print(b)
    x, y, w, h = int(b[1]), int(b[2]), int(b[3]), int(b[4])
    cv2.rectangle(img, (x, hImg - y), (w, hImg - h), (50, 50, 255), 1)
    cv2.putText(img, b[0], (x, hImg - y + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (50, 205, 50), 1)

  cv2.imshow('Detected text', img)
  return 1

def boxes_image(orig_image_arr):
  orig_image_arr=process_image(orig_image_arr)
  otsu_thresh_image=PIL.Image.fromarray(orig_image_arr)
  otsu_thresh_image=otsu_thresh_image.convert('RGB')

crop = True 

if __name__ == '__main__':
  #To Do:
  #Calibration sequence for first image to determine image processing
  #Choose font-- 7 segment or normal

  img=cv2.imread('C:/fun/1234.jpg')
  cv2.imshow('img',img)

  edged_image=cnvt_edged_image(img)
  text = ocr_image(img)
  boxed_image = ocr_image_boxed(img)

  print('text detected:',text)
  cv2.waitKey(0)


