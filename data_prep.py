import os
import multiprocessing as mp
import math
import cv2
import pandas as pd


def remove_hair_inpaint(image):
    grayScale = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    kernel = cv2.getStructuringElement(1, (9, 9))
    blackhat = cv2.morphologyEx(grayScale, cv2.MORPH_BLACKHAT, kernel)  # Black hat filter
    bhg = cv2.GaussianBlur(blackhat, (3, 3), cv2.BORDER_DEFAULT)  # Gaussian filter
    ret, mask = cv2.threshold(bhg, 10, 255, cv2.THRESH_BINARY)  # Binary thresholding (MASK)
    return cv2.inpaint(image, mask, 6, cv2.INPAINT_NS)  # Replace pixels of the mask


def resize_cvt_color(sample, args):
    image_path = os.path.join(args['dir_dict']['data'], sample['image'])
    new_path = os.path.join(args['dir_dict']['image_folder'], sample['image'])

    def resize(image, size):
        resize = int(size) / max(image.shape)
        return cv2.resize(src=image, dsize=None, fx=resize, fy=resize, interpolation=cv2.INTER_NEAREST_EXACT)

    if not os.path.isfile(new_path):
        image = cv2.imread(image_path)
        image = resize(image, 500)  # Resize to 500pxl
        image = remove_hair_inpaint(image)
        if int(args['image_size']) != 500:
            image = resize(image, args['image_size'])
        dx = (image.shape[0] - image.shape[1]) / 2  # Compare height-width
        tblr = [math.ceil(abs(dx)), math.floor(abs(dx)), 0, 0]  # Pad top-bottom
        if dx > 0:  # If height > width
            tblr = tblr[2:] + tblr[:2]  # Pad left-right
        image = cv2.copyMakeBorder(image, *tblr, borderType=cv2.BORDER_CONSTANT)
        if args['colour'] == 'grey':
            image = cv2.cvtColor(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)  # 3-channel gray
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        if not cv2.imwrite(new_path, image):
            with open("failed_to_covert.txt", "a") as f:
                f.write(f"{image_path} 'to '{new_path}'\n'")


def check_create_dataset(args, force=False):
    os.environ['OMP_NUM_THREADS'] = '1'
    if not os.path.exists(args['dir_dict']['image_folder']) or force is True:
        print(f"Checking dataset in {args['dir_dict']['image_folder']}\nDataset Specs: img_size: {args['image_size']}, colour: {args['colour']}")
        samples = pd.read_csv(args['dir_dict']['data_csv']['train']).append(
            pd.read_csv(args['dir_dict']['data_csv']['val'])).append(
            pd.read_csv(args['dir_dict']['data_csv']['test'])).append(
            pd.read_csv(args['dir_dict']['data_csv']['isic20_test']))
        pool = mp.Pool(mp.cpu_count())
        pool.starmap(resize_cvt_color, [(sample, args) for _, sample in samples.iterrows()])
        pool.close()
        print('Done!')
    else:
        print(f"Dataset {args['dir_dict']['image_folder']} exists!")
