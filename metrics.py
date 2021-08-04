import tensorflow.keras.backend as K
from tensorflow.keras.metrics import AUC
import tensorflow_addons as tfa


def metrics(classes):
    # macro: unweighted mean for each class
    auc = AUC(multi_label=True)
    f1_weighted = tfa.metrics.F1Score(num_classes=classes, average='weighted', name='f1_weighted')
    return [auc, f1_weighted]


def sensitivity(y_true, y_pred):
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
    return true_positives / (possible_positives + K.epsilon())


def specificity(y_true, y_pred):
    true_negatives = K.sum(K.round(K.clip((1-y_true) * (1-y_pred), 0, 1)))
    possible_negatives = K.sum(K.round(K.clip(1-y_true, 0, 1)))
    return true_negatives / (possible_negatives + K.epsilon())
