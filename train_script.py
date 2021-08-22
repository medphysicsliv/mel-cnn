import os

import tensorflow as tf
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.metrics import AUC

from data_pipe import MelData
from metrics import calc_metrics
from model import model_fn
from custom_losses import PerClassWeightedCategoricalCrossentropy
from callbacks import LaterCheckpoint, EnrTensorboard, TestCallback


def training(args):
    strategy = tf.distribute.MirroredStrategy()
    args['replicas'] = strategy.num_replicas_in_sync
    datasets = MelData(args=args)
    args['train_data'] = datasets.get_dataset(pick_dataset='train')
    args['val_data'] = datasets.get_dataset(pick_dataset='val')
    args['test_data'] = datasets.get_dataset(pick_dataset='test')
    args['isic20_test'] = datasets.get_dataset(pick_dataset='isic20_test')
    if args['test'] or args['validate']:
        args['dir_dict']['model_path'] = args['test_model']
        args['dir_dict']['trial'] = os.path.dirname(args['dir_dict']['model_path'])
        model = tf.keras.models.load_model(args['dir_dict']['model_path'], compile=False)
        if args['test']:
            calc_metrics(args=args, model=model, dataset=args['isic20_test'], dataset_type='isic20_test')
        else:
            calc_metrics(args=args, model=model, dataset=args['val_data'], dataset_type='validation')
            calc_metrics(args=args, model=model, dataset=args['test_data'], dataset_type='test')
            if args['task'] in ('ben_mal', '5cls'):
                calc_metrics(args=args, model=model, dataset=args['isic20_test'], dataset_type='isic20_test')
    else:
        with open(args['dir_dict']['hparams_logs'], 'a') as f:
            [f.write(': '.join([key.capitalize().rjust(len(max(args.keys(), key=len))), str(args[key])]) + '\n')
             for key in args.keys() if key not in ('dir_dict', 'hparams', 'train_data', 'val_data', 'test_data', 'isic20_test')]

        optimizer = {'adam': tf.keras.optimizers.Adam, 'ftrl': tf.keras.optimizers.Ftrl,
                     'sgd': tf.keras.optimizers.SGD, 'rmsprop': tf.keras.optimizers.RMSprop,
                     'adadelta': tf.keras.optimizers.Adadelta, 'adagrad': tf.keras.optimizers.Adagrad,
                     'adamax': tf.keras.optimizers.Adamax, 'nadam': tf.keras.optimizers.Nadam}[args['optimizer']](learning_rate=args['learning_rate'] * args['replicas'])
        with strategy.scope():
            custom_model = model_fn(args=args)
            with open(args['dir_dict']['trial'] + '/model_summary.txt', 'w') as f:
                custom_model.summary(print_fn=lambda x: f.write(x + '\n'))

            custom_model.compile(optimizer=optimizer,
                                 loss=PerClassWeightedCategoricalCrossentropy(args=args),
                                 metrics=[AUC(multi_label=True)])
        # --------------------------------------------------- Callbacks ---------------------------------------------- #
        callbacks = [LaterCheckpoint(filepath=args['dir_dict']['model_path'], save_best_only=True, start_at=20),
                     EnrTensorboard(log_dir=args['dir_dict']['logs'], val_data=args['val_data'], class_names=args['class_names']),
                     ReduceLROnPlateau(factor=0.75, patience=10),
                     EarlyStopping(verbose=args['verbose'], patience=20),
                     TestCallback(args=args)]
        # ------------------------------------------------- Train model ---------------------------------------------- #
        custom_model.fit(x=args['train_data'], epochs=args['epochs'],
                         validation_data=args['val_data'],
                         callbacks=callbacks, verbose=args['verbose'])
