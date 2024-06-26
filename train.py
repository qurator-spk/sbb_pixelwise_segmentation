import os
import sys
import tensorflow as tf
from tensorflow.compat.v1.keras.backend import set_session
import warnings
from tensorflow.keras.optimizers import *
from sacred import Experiment
from models import *
from utils import *
from metrics import *
from tensorflow.keras.models import load_model
from tqdm import tqdm


def configuration():
    config = tf.compat.v1.ConfigProto()
    config.gpu_options.allow_growth = True
    session = tf.compat.v1.Session(config=config)
    set_session(session)


def get_dirs_or_files(input_data):
    if os.path.isdir(input_data):
        image_input, labels_input = os.path.join(input_data, 'images/'), os.path.join(input_data, 'labels/')
        # Check if training dir exists
        assert os.path.isdir(image_input), "{} is not a directory".format(image_input)
        assert os.path.isdir(labels_input), "{} is not a directory".format(labels_input)
    return image_input, labels_input


ex = Experiment()


@ex.config
def config_params():
    n_classes = None  # Number of classes. In the case of binary classification this should be 2.
    n_epochs = 1  # Number of epochs.
    input_height = 224 * 1  # Height of model's input in pixels.
    input_width = 224 * 1  # Width of model's input in pixels.
    weight_decay = 1e-6  # Weight decay of l2 regularization of model layers.
    n_batch = 1  # Number of batches at each iteration.
    learning_rate = 1e-4  # Set the learning rate.
    patches = False  # Divides input image into smaller patches (input size of the model) when set to true. For the model to see the full image, like page extraction, set this to false.
    augmentation = False  # To apply any kind of augmentation, this parameter must be set to true.
    flip_aug = False  # If true, different types of flipping will be applied to the image. Types of flips are defined with "flip_index" in train.py.
    blur_aug = False  # If true, different types of blurring will be applied to the image. Types of blur are defined with "blur_k" in train.py.
    scaling = False  # If true, scaling will be applied to the image. The amount of scaling is defined with "scales" in train.py.
    binarization = False  # If true, Otsu thresholding will be applied to augment the input with binarized images.
    dir_train = None  # Directory of training dataset with subdirectories having the names "images" and "labels".
    dir_eval = None  # Directory of validation dataset with subdirectories having the names "images" and "labels".
    dir_output = None  # Directory where the output model will be saved.
    pretraining = False  # Set to true to load pretrained weights of ResNet50 encoder.
    scaling_bluring = False  # If true, a combination of scaling and blurring will be applied to the image.
    scaling_binarization = False  # If true, a combination of scaling and binarization will be applied to the image.
    scaling_flip = False  # If true, a combination of scaling and flipping will be applied to the image.
    thetha = [10, -10]  # Rotate image by these angles for augmentation.
    blur_k = ['blur', 'gauss', 'median']  # Blur image for augmentation.
    scales = [0.5, 2]  # Scale patches for augmentation.
    flip_index = [0, 1, -1]  # Flip image for augmentation.
    continue_training = False  # Set to true if you would like to continue training an already trained a model.
    index_start = 0  # Index of model to continue training from. E.g. if you trained for 3 epochs and last index is 2, to continue from model_1.h5, set "index_start" to 3 to start naming model with index 3.
    dir_of_start_model = ''  # Directory containing pretrained encoder to continue training the model.
    is_loss_soft_dice = False  # Use soft dice as loss function. When set to true, "weighted_loss" must be false.
    weighted_loss = False  # Use weighted categorical cross entropy as loss fucntion. When set to true, "is_loss_soft_dice" must be false.
    data_is_provided = False  # Only set this to true when you have already provided the input data and the train and eval data are in "dir_output".


@ex.automain
def run(n_classes, n_epochs, input_height,
        input_width, weight_decay, weighted_loss,
        index_start, dir_of_start_model, is_loss_soft_dice,
        n_batch, patches, augmentation, flip_aug,
        blur_aug, scaling, binarization,
        blur_k, scales, dir_train, data_is_provided,
        scaling_bluring, scaling_binarization, rotation,
        rotation_not_90, thetha, scaling_flip, continue_training,
        flip_index, dir_eval, dir_output, pretraining, learning_rate):
    if data_is_provided:
        dir_train_flowing = os.path.join(dir_output, 'train')
        dir_eval_flowing = os.path.join(dir_output, 'eval')

        dir_flow_train_imgs = os.path.join(dir_train_flowing, 'images')
        dir_flow_train_labels = os.path.join(dir_train_flowing, 'labels')

        dir_flow_eval_imgs = os.path.join(dir_eval_flowing, 'images')
        dir_flow_eval_labels = os.path.join(dir_eval_flowing, 'labels')

        configuration()

    else:
        dir_img, dir_seg = get_dirs_or_files(dir_train)
        dir_img_val, dir_seg_val = get_dirs_or_files(dir_eval)

        # make first a directory in output for both training and evaluations in order to flow data from these directories.
        dir_train_flowing = os.path.join(dir_output, 'train')
        dir_eval_flowing = os.path.join(dir_output, 'eval')

        dir_flow_train_imgs = os.path.join(dir_train_flowing, 'images/')
        dir_flow_train_labels = os.path.join(dir_train_flowing, 'labels/')

        dir_flow_eval_imgs = os.path.join(dir_eval_flowing, 'images/')
        dir_flow_eval_labels = os.path.join(dir_eval_flowing, 'labels/')

        if os.path.isdir(dir_train_flowing):
            os.system('rm -rf ' + dir_train_flowing)
            os.makedirs(dir_train_flowing)
        else:
            os.makedirs(dir_train_flowing)

        if os.path.isdir(dir_eval_flowing):
            os.system('rm -rf ' + dir_eval_flowing)
            os.makedirs(dir_eval_flowing)
        else:
            os.makedirs(dir_eval_flowing)

        os.mkdir(dir_flow_train_imgs)
        os.mkdir(dir_flow_train_labels)

        os.mkdir(dir_flow_eval_imgs)
        os.mkdir(dir_flow_eval_labels)

        # set the gpu configuration
        configuration()

        # writing patches into a sub-folder in order to be flowed from directory.
        provide_patches(dir_img, dir_seg, dir_flow_train_imgs,
                        dir_flow_train_labels,
                        input_height, input_width, blur_k, blur_aug,
                        flip_aug, binarization, scaling, scales, flip_index,
                        scaling_bluring, scaling_binarization, rotation,
                        rotation_not_90, thetha, scaling_flip,
                        augmentation=augmentation, patches=patches)

        provide_patches(dir_img_val, dir_seg_val, dir_flow_eval_imgs,
                        dir_flow_eval_labels,
                        input_height, input_width, blur_k, blur_aug,
                        flip_aug, binarization, scaling, scales, flip_index,
                        scaling_bluring, scaling_binarization, rotation,
                        rotation_not_90, thetha, scaling_flip,
                        augmentation=False, patches=patches)

    if weighted_loss:
        weights = np.zeros(n_classes)
        if data_is_provided:
            for obj in os.listdir(dir_flow_train_labels):
                try:
                    label_obj = cv2.imread(dir_flow_train_labels + '/' + obj)
                    label_obj_one_hot = get_one_hot(label_obj, label_obj.shape[0], label_obj.shape[1], n_classes)
                    weights += (label_obj_one_hot.sum(axis=0)).sum(axis=0)
                except:
                    pass
        else:

            for obj in os.listdir(dir_seg):
                try:
                    label_obj = cv2.imread(dir_seg + '/' + obj)
                    label_obj_one_hot = get_one_hot(label_obj, label_obj.shape[0], label_obj.shape[1], n_classes)
                    weights += (label_obj_one_hot.sum(axis=0)).sum(axis=0)
                except:
                    pass

        weights = 1.00 / weights

        weights = weights / float(np.sum(weights))
        weights = weights / float(np.min(weights))
        weights = weights / float(np.sum(weights))

    if continue_training:
        if is_loss_soft_dice:
            model = load_model(dir_of_start_model, compile=True, custom_objects={'soft_dice_loss': soft_dice_loss})
        if weighted_loss:
            model = load_model(dir_of_start_model, compile=True,
                               custom_objects={'loss': weighted_categorical_crossentropy(weights)})
        if not is_loss_soft_dice and not weighted_loss:
            model = load_model(dir_of_start_model, compile=True)
    else:
        # get our model.
        index_start = 0
        model = resnet50_unet(n_classes, input_height, input_width, weight_decay, pretraining)

    # if you want to see the model structure just uncomment model summary.
    # model.summary()

    if not is_loss_soft_dice and not weighted_loss:
        model.compile(loss='categorical_crossentropy',
                      optimizer=Adam(lr=learning_rate), metrics=['accuracy'])
    if is_loss_soft_dice:
        model.compile(loss=soft_dice_loss,
                      optimizer=Adam(lr=learning_rate), metrics=['accuracy'])

    if weighted_loss:
        model.compile(loss=weighted_categorical_crossentropy(weights),
                      optimizer=Adam(lr=learning_rate), metrics=['accuracy'])

    # generating train and evaluation data
    train_gen = data_gen(dir_flow_train_imgs, dir_flow_train_labels, batch_size=n_batch,
                         input_height=input_height, input_width=input_width, n_classes=n_classes)
    val_gen = data_gen(dir_flow_eval_imgs, dir_flow_eval_labels, batch_size=n_batch,
                       input_height=input_height, input_width=input_width, n_classes=n_classes)

    for i in tqdm(range(index_start, n_epochs + index_start)):
        model.fit_generator(
            train_gen,
            steps_per_epoch=int(len(os.listdir(dir_flow_train_imgs)) / n_batch) - 1,
            validation_data=val_gen,
            validation_steps=1,
            epochs=1)
        model.save(dir_output + '/' + 'model_' + str(i))

    # os.system('rm -rf '+dir_train_flowing)
    # os.system('rm -rf '+dir_eval_flowing)

    # model.save(dir_output+'/'+'model'+'.h5')
