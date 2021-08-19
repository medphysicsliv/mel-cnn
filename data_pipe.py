import os
from config import DATA_MAP, BEN_MAL_MAP, NEV_MEL_MAP, CLASS_NAMES, MAIN_DIR, NP_RNG
import tensorflow as tf
from tensorflow.keras.applications import xception, inception_v3, efficientnet
import tensorflow_addons as tfa
import numpy as np
import pandas as pd


class MelData:
    def __init__(self, args: dict):
        self.args = args
        self.batch_size = self.args['batch_size'] * self.args['replicas']
        self.train_data_df = self.preproc_df('train')
        self.val_data_df = self.preproc_df('val')
        self.test_data_df = self.preproc_df('test')
        self.TF_RNG = tf.random.Generator.from_non_deterministic_state()
        self.class_counts = dict(self.train_data_df['class'].value_counts())
        self.image_type_counts = dict(self.train_data_df['image_type'].value_counts())
        self.datasets = {'train': self.ohe_map(self.set_sample_weight(self.train_data_df).sample(frac=self.args['dataset_frac'], random_state=NP_RNG.bit_generator)),
                         'val': self.ohe_map(self.set_sample_weight(self.val_data_df).sample(frac=self.args['dataset_frac'], random_state=NP_RNG.bit_generator)),
                         'test': self.ohe_map(self.set_sample_weight(self.test_data_df)),
                         'isic20_test': self.ohe_map(self.preproc_df('isic20_test'))}
        for i in ['all', 'train', 'val', 'test']:
            self.data_info(i)

    def preproc_df(self, mode):
        df = pd.read_csv(self.args['dir_dict']['data_csv'][mode])
        df['image'] = df['image'].apply(lambda x: os.path.join(self.args['dir_dict']['image_folder'], x))
        if self.args['mode'] == 'ben_mal':
            mapper = BEN_MAL_MAP
        elif self.args['mode'] == 'nev_mel':
            mapper = NEV_MEL_MAP
        else:
            mapper = None
        df.replace(to_replace=mapper, inplace=True)
        if self.args['image_type'] != 'both':  # Keep derm or clinic, samples.
            df.drop(df[df['image_type'] != DATA_MAP['image_type'][self.args['image_type']]].index, errors='ignore', inplace=True)
        if not mode == 'isic20_test':
            if self.args['mode'] == 'nev_mel':
                df.drop(df[df['class'] == 2].index, errors='ignore', inplace=True)
            if self.args['mode'] == '5cls':
                df.drop(df[df['class'] == 5].index, errors='ignore', inplace=True)
        return df

    def set_sample_weight(self, df):
        weights_per_class = np.divide(len(self.train_data_df),
                                      np.multiply(self.args['num_classes'], [self.class_counts[k]for k in sorted(self.class_counts)]))
        if len(self.image_type_counts) > 1:
            weights_per_image_type = np.divide(len(self.train_data_df),
                                               np.multiply(len(self.image_type_counts), [self.image_type_counts[k] for k in sorted(self.image_type_counts)]))
        else:
            weights_per_image_type = [0]
        weights_per_image_type = np.sqrt(weights_per_image_type)  # Through sqrt

        for idx1, _class in enumerate(sorted(self.class_counts)):
            for idx2, image_type in enumerate(sorted(self.image_type_counts)):
                if self.args['no_image_weights']:
                    sample_weight = 1.  # weights_per_class[idx1]
                else:
                    sample_weight = weights_per_image_type[idx2]  # weights_per_class[idx1] + weights_per_image_type[idx2]
                df.loc[(df['image_type'] == image_type) & (df['class'] == _class), 'sample_weights'] = sample_weight
        df['sample_weights'] /= df['sample_weights'].min()
        return df

    def ohe_map(self, features):
        ohe_features = {'image': features['image'],
                        'image_type': tf.keras.backend.one_hot(indices=features['image_type'], num_classes=2),
                        'sex': tf.keras.backend.one_hot(indices=features['sex'], num_classes=2),
                        'age_approx': tf.keras.backend.one_hot(indices=features['age_approx'], num_classes=10),
                        'location': tf.keras.backend.one_hot(indices=features['location'], num_classes=6)}
        if 'isic20_test' in features['dataset_id'].unique():
            return ohe_features
        else:
            labels = {'class': tf.keras.backend.one_hot(indices=features['class'], num_classes=self.args['num_classes'])}
            sample_weights = tf.convert_to_tensor(features['sample_weights'].astype(float))
            return ohe_features, labels, sample_weights

    def data_info(self, mode):
        dataset_info_dict = {}
        image_type_inv = {}
        if mode == 'all':
            df = self.train_data_df.append(self.val_data_df).append(self.test_data_df)
        elif mode == 'train':
            df = self.train_data_df
        elif mode == 'val':
            df = self.val_data_df
        else:
            df = self.test_data_df
        for (key, value) in DATA_MAP['image_type'].items():
            image_type_inv[value] = key
        for dataset_id in df['dataset_id'].unique():
            dataset_part = df[df.loc[:, 'dataset_id'] == dataset_id]  # fraction per class
            dataset_img_type_dict = {}
            for image_type in dataset_part['image_type'].unique():
                dataset_image_part = dataset_part[dataset_part.loc[:, 'image_type'] == image_type]
                dataset_class_dict = {}
                for k, v in dataset_image_part['class'].value_counts().items():
                    dataset_class_dict[CLASS_NAMES[self.args['mode']][k]] = v
                dataset_img_type_dict[image_type_inv[image_type]] = dataset_class_dict
            dataset_info_dict[dataset_id] = dataset_img_type_dict
        info = pd.DataFrame(dataset_info_dict).stack().apply(pd.Series)
        info = info[sorted(info.columns)]
        info.fillna(0, inplace=True)
        save_path = os.path.join(MAIN_DIR, 'data_info', f"{self.args['mode']}", f"{self.args['image_type']}", f"{mode}_data_info")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        info.to_html(save_path + '.html', bold_rows=False, border=4)
        info.to_csv(save_path + '.csv')
        return dataset_info_dict

    def info(self):
        image_type_inv = {}
        for (key, value) in DATA_MAP['image_type'].items():
            image_type_inv[value] = key
        info_w = ''
        for _image_type in self.image_type_counts:
            info_w += image_type_inv[_image_type] + '\n'
            for _class in sorted(self.class_counts):
                a = np.round(np.squeeze(self.train_data_df.loc[(self.train_data_df['image_type'] == _image_type) & (
                        self.train_data_df['class'] == _class), 'sample_weights'].unique()), 3)
                info_w += ' '.join([CLASS_NAMES[self.args['mode']][_class].rjust(len(max(CLASS_NAMES[self.args['mode']], key=len))), str(a)+'\n'])

        return f"Train Length: {len(self.datasets['train'][1]['class'])}\n" \
               f"Train Class Samples: {np.sum(self.datasets['train'][1]['class'], axis=0)}\n" \
               f"Validation Length: {len(self.datasets['val'][1]['class'])}\n" \
               f"Validation Class Samples: {np.sum(self.datasets['val'][1]['class'], axis=0)}\n" \
               f"Test Length: {len(self.datasets['test'][1]['class'])}\n" \
               f"Test Class Samples: {np.sum(self.datasets['test'][1]['class'], axis=0)}\n" \
               'Weights\n' + info_w

    def get_dataset(self, mode=None, repeat=1):
        dataset = self.datasets[mode]
        if self.args['only_image']:
            if isinstance(dataset, tuple):
                dataset[0].pop('image_type')
                dataset[0].pop('sex')
                dataset[0].pop('age_approx')
                dataset[0].pop('location')
            else:
                dataset.pop('image_type')
                dataset.pop('sex')
                dataset.pop('age_approx')
                dataset.pop('location')

        def tf_imread(sample, label=None, sample_weight=None):
            image_path = sample['image']
            sample['image'] = tf.image.decode_image(tf.io.read_file(sample['image']), channels=3)
            if self.args['test']:
                pass
                # sample['image'] = tf.numpy_function(hair_removal, [sample['image']], np.uint8)
            sample['image'] = {'xept': xception.preprocess_input, 'incept': inception_v3.preprocess_input,
                               'effnet0': efficientnet.preprocess_input,
                               'effnet1': efficientnet.preprocess_input}[self.args['model']](sample['image'])
            sample['image'] = tf.reshape(tensor=sample['image'], shape=self.args['input_shape'])
            if mode == 'isic20_test':
                return sample, image_path
            else:
                return sample, label, sample_weight

        def image_augm(sample, label, sample_weight):
            trans_rat = self.args['image_size'] * 0.05
            seeds = self.TF_RNG.make_seeds(5)
            sample['image'] = tf.image.stateless_random_flip_up_down(image=sample['image'], seed=seeds[:, 0])
            sample['image'] = tf.image.stateless_random_flip_left_right(image=sample['image'], seed=seeds[:, 1])
            sample['image'] = tf.image.stateless_random_brightness(image=sample['image'], max_delta=0.1, seed=seeds[:, 2])
            sample['image'] = tf.image.stateless_random_contrast(image=sample['image'], lower=.5, upper=1.5, seed=seeds[:, 3])
            sample['image'] = tf.image.stateless_random_saturation(image=sample['image'], lower=0.8, upper=1.2, seed=seeds[:, 4])
            sample['image'] = tfa.image.sharpness(image=tf.cast(sample['image'], dtype=tf.float32), factor=self.TF_RNG.uniform(shape=[1], maxval=2., dtype=tf.float32), name='Sharpness')
            sample['image'] = tfa.image.translate(sample['image'], translations=self.TF_RNG.uniform(shape=[2], minval=-trans_rat, maxval=trans_rat, dtype=tf.float32), name='Translation')
            sample['image'] = tfa.image.rotate(images=sample['image'], angles=tf.cast(self.TF_RNG.uniform(shape=[1], minval=0, maxval=360, dtype=tf.int32), dtype=tf.float32), name='Rotation')
            sample['image'] = tf.cond(tf.math.less_equal(self.TF_RNG.uniform(shape=[1], maxval=1., dtype=tf.float32), 0.5),
                                      lambda: tfa.image.gaussian_filter2d(image=sample['image'], sigma=float(NP_RNG.random(size=1)) * 2, filter_shape=5, name='Gaussian_filter'),
                                      lambda: sample['image'])
            return sample, label, sample_weight

        dataset = tf.data.Dataset.from_tensor_slices(dataset)
        dataset = dataset.map(tf_imread, num_parallel_calls=tf.data.experimental.AUTOTUNE)
        if not self.args['test']:
            dataset = dataset.cache()
        if mode == 'train':
            dataset = dataset.map(image_augm, num_parallel_calls=tf.data.experimental.AUTOTUNE).prefetch(buffer_size=tf.data.experimental.AUTOTUNE)
        dataset = dataset.batch(self.batch_size)
        options = tf.data.Options()
        options.experimental_threading.max_intra_op_parallelism = 1
        options.experimental_distribute.auto_shard_policy = tf.data.experimental.AutoShardPolicy.DATA
        dataset = dataset.with_options(options)
        dataset = dataset.repeat(repeat)
        return dataset.prefetch(buffer_size=tf.data.experimental.AUTOTUNE)
