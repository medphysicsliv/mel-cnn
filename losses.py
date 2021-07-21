import tensorflow as tf


def weighted_categorical_crossentropy(weights):
    """
    A weighted version of keras.objectives.categorical_crossentropy

    Variables:
        weights: numpy array of shape (C,) where C is the number of classes

    Usage:
        weights = np.array([0.5,2,10]) # Class one at 0.5, class 2 twice the normal weights, class 3 10x.
        loss = weighted_categorical_crossentropy(weights)
        model.compile(loss=loss,optimizer='adam')
    """

    weights = tf.keras.backend.variable(weights)

    def loss(y_true, y_pred):
        """ y_true: One-hot label
            y_pred: Softmax output."""
        # clip to prevent NaN's and Inf's
        y_pred = tf.clip_by_value(y_pred, tf.keras.backend.epsilon(), 1 - tf.keras.backend.epsilon())
        # calc
        w_loss = y_true * tf.math.log(y_pred) * weights
        w_loss = -tf.reduce_sum(w_loss, -1)
        return w_loss

    return loss


def custom_loss(weights):
    with tf.name_scope('Weights'):
        weights = tf.keras.backend.variable(weights)
    with tf.name_scope('epsilon'):
        e = tf.keras.backend.epsilon()

    def total_loss(y_true, y_pred):
        def log_dice_loss(dice_y_true, dice_y_pred):
            """both tensors are [b, h, w, classes] and y_pred is in probs form"""
            with tf.name_scope('Weighted_Generalized_Dice_Log_Loss'):
                with tf.name_scope('Axis_to_reduce'):
                    reduce_axis = list(range(len(dice_y_pred.shape)-1))
                with tf.name_scope('Numerator'):
                    numerator = tf.multiply(x=weights, y=tf.reduce_sum(dice_y_true * dice_y_pred, axis=reduce_axis))
                with tf.name_scope('Denominator'):
                    denominator = tf.multiply(x=weights, y=tf.reduce_sum(dice_y_true + dice_y_pred, axis=reduce_axis))
                # Dice Score per class
                with tf.name_scope('Dice_Division'):
                    division = tf.divide(x=tf.add(x=numerator, y=e),
                                         y=tf.add(denominator, y=e))
                    dice = tf.multiply(x=2., y=division)
                with tf.name_scope('Batch_loss'):
                    dice = tf.math.reduce_mean(- tf.math.log(dice))
                return dice

        def weighted_crossentropy(wce_y_true, wce_y_pred):
            """ y_true: One-hot label
                y_pred: Softmax output."""
            with tf.name_scope('Weighted_Crossentropy_Loss'):
                w_loss = tf.keras.backend.categorical_crossentropy(tf.multiply(x=weights, y=wce_y_true), wce_y_pred)  # Loss per sample
                return tf.reduce_mean(w_loss)  # Batch loss

        return tf.math.multiply(.6, log_dice_loss(y_true, y_pred)) + tf.math.multiply(0.4, weighted_crossentropy(y_true, y_pred))
    return total_loss