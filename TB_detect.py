import argparse
import cv2
import os
import time
import numpy as np
import torch
#from google.colab.patches import cv2_imshow

from models.experimental import attempt_load
from utils.general import non_max_suppression
from utils.torch_utils import select_device

def letterbox(img, new_shape=(640, 640), color=(114, 114, 114), auto=True, scaleFill=False, scaleup=True):
    # Resize image to a 32-pixel-multiple rectangle https://github.com/ultralytics/yolov3/issues/232
    shape = img.shape[:2]  # current shape [height, width]
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)

    # Scale ratio (new / old)
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    if not scaleup:  # only scale down, do not scale up (for better test mAP)
        r = min(r, 1.0)

    # Compute padding
    ratio = r, r  # width, height ratios
    new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
    dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # wh padding
    if auto:  # minimum rectangle
        dw, dh = np.mod(dw, 64), np.mod(dh, 64)  # wh padding
    elif scaleFill:  # stretch
        dw, dh = 0.0, 0.0
        new_unpad = new_shape
        ratio = new_shape[0] / shape[1], new_shape[1] / shape[0]  # width, height ratios

    dw /= 2  # divide padding into 2 sides
    dh /= 2

    if shape[::-1] != new_unpad:  # resize
        img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)  # add border
    return img, ratio, (dw, dh)

#直接判一個大圖是陽性還是陰性
def img_class_predict(imgs, threshold = 1., score_threshold = 0.4):
    top, down = 0, 576
    rag = 528
    N = 0
    #predict_bbox = []
    #predict_bbox_dict = {}
    for h in range(4):
        left, right = 0, 576
        for w in range(4):
            img_crop=imgs[left:right,top:down]
            #Padded resize
            img = letterbox(img_crop, new_shape=576)[0]
            #Convert
            img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB, to 3x416x416
            img = np.ascontiguousarray(img)
            img = torch.from_numpy(img).to(device)
            img = img.half() if half else img.float()  # uint8 to fp16/32
            img /= 255.0  # 0 - 255 to 0.0 - 1.0
            if img.ndimension() == 3:
                img = img.unsqueeze(0)
            model.eval()
            pred = model(img, augment='store_true')[0]
            pred_nms = non_max_suppression(pred, score_threshold, 0.9, agnostic='store_true')#0.4表示要多少信心度以上才選
            if pred_nms != [None]:
                N += int(len(pred_nms[0]))
            else: pass
            
            left += rag
            right += rag
        top += rag
        down += rag
    if N >= threshold:
        #predict_bbox_dict[img_name] = predict_bbox
        return True
    else:return False

def predict(img_path,threshold):
  img = cv2.imread(img_path)
  predict_t=img_class_predict(img,score_threshold=threshold)
  return predict_t

#視覺化完整的一張圖
def bb_visualization(imgs,  score_threshold = 0.4):
    top, down = 0, 576
    rag = 528
    N = 0
    predict_bbox = []
    reshape_ratio =1
    #predict_bbox_dict = {}
    for h in range(4):
        left, right = 0, 576
        for w in range(4):
            img_crop=imgs[left:right,top:down]
            #Padded resize
            img = letterbox(img_crop, new_shape=576)[0]
            #Convert
            img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB, to 3x416x416
            img = np.ascontiguousarray(img)
            img = torch.from_numpy(img).to(device)
            img = img.half() if half else img.float()  # uint8 to fp16/32
            img /= 255.0  # 0 - 255 to 0.0 - 1.0
            if img.ndimension() == 3:
                img = img.unsqueeze(0)
            model.eval()
            pred = model(img, augment='store_true')[0]
            pred_nms = non_max_suppression(pred, score_threshold, 0.5, agnostic='store_true')#0.4表示要多少信心度以上才選
            if pred_nms != [None]:
                for i in range(len(pred_nms[0])):
                    bb_left = int(left+pred_nms[0][i][0]*reshape_ratio)
                    bb_top = int(top+pred_nms[0][i][1]*reshape_ratio)
                    bb_right = int(left+pred_nms[0][i][2]*reshape_ratio)
                    bb_down = int(top+pred_nms[0][i][3]*reshape_ratio)
                    predict_bbox.append([bb_left, bb_top, bb_right, bb_down, float(pred_nms[0][i][4])])
                
                
            else: pass
            
            left += rag
            right += rag
        top += rag
        down += rag
    return predict_bbox


def visualization(img_path):
    img0 = cv2.imread(img_path)
    output = bb_visualization(img0,score_threshold = 0.5)
    #visualization
    for i in range(len(output)):
        cv2.rectangle(img0,(output[i][0],output[i][1]),(output[i][2],output[i][3]),(255,255,255),2)
        cv2.putText(img0,str(round(output[i][4],2)),(output[i][0]-5,output[i][1]-5),cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, color=(0,255,255),thickness=2)
    return img0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--img_path', type=str, default='', help='paht of image to predict')
    parser.add_argument('--weight', type=str, default='', help='trained_model_weight')
    parser.add_argument('--threshold', type=float, default=0.7, help='confidence threshold')
    #parser.add_argument('--show_output', type=bool, default=False, help='confidence threshold')#目前還無法在colab上顯示,所以先不開放
    opt = parser.parse_args()
    #print(opt)
    weights, imgsz = \
    opt.weight, 576
    device = select_device('')
    half = device.type != 'cpu' 
    model = attempt_load(weights, map_location=device)
    model.to(device).eval()
    if half:
        model.half()  # to FP16
    outcome = predict(opt.img_path,opt.threshold)
    if outcome:
        print("This image is positive image")
    else:
        print("This image is negative image")
#     if opt.show_output:
#         img = visualization(opt.img_path)
#         cv2_imshow(img)
        
        
