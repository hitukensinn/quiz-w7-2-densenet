"""Contains a variant of the densenet model definition."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf

slim = tf.contrib.slim
tf.ConfigProto(log_device_placement=True,allow_soft_placement=True)


def trunc_normal(stddev): return tf.truncated_normal_initializer(stddev=stddev)


def bn_act_conv_drp(current, num_outputs, kernel_size, scope='block'):
    current = slim.batch_norm(current, scope=scope + '_bn')
    current = tf.nn.relu(current)
    current = slim.conv2d(current, num_outputs, kernel_size, scope=scope + '_conv')
    current = slim.dropout(current, scope=scope + '_dropout')
    return current


def block(net, layers, growth, scope='block'):
    for idx in range(layers):
        bottleneck = bn_act_conv_drp(net, 4 * growth, [1, 1],
                                     scope=scope + '_conv1x1' + str(idx))
        tmp = bn_act_conv_drp(bottleneck, growth, [3, 3],
                              scope=scope + '_conv3x3' + str(idx))
        net = tf.concat(axis=3, values=[net, tmp])
    return net

def transition(current, num_outputs, scope='transition'):
    current = slim.batch_norm(current, scope=scope + '_tn')
    current = slim.conv2d(current, num_outputs, [1, 1], scope=scope + '_conv')
    current = slim.max_pool2d(current, [2, 2], scope=scope + '_pool')
    return current


def densenet(images, num_classes=1001, is_training=False,
             dropout_keep_prob=0.8,
             scope='densenet'):
    """Creates a variant of the densenet model.

      images: A batch of `Tensors` of size [batch_size, height, width, channels].
      num_classes: the number of classes in the dataset.
      is_training: specifies whether or not we're currently training the model.
        This variable will determine the behaviour of the dropout layer.
      dropout_keep_prob: the percentage of activation values that are retained.
      prediction_fn: a function to get predictions out of logits.
      scope: Optional variable_scope.

    Returns:
      logits: the pre-softmax activations, a tensor of size
        [batch_size, `num_classes`]
      end_points: a dictionary from components of the network to the corresponding
        activation.
    """
    growth = 24
    compression_rate = 0.5

    def reduce_dim(input_feature):
        return int(int(input_feature.shape[-1]) * compression_rate)

    end_points = {}

    with tf.variable_scope(scope, 'DenseNet', [images, num_classes]):
        with slim.arg_scope(bn_drp_scope(is_training=is_training,
                                         keep_prob=dropout_keep_prob)) as ssc:
            pass
            ##########################
            nchannels = images.shape[3]
            current = slim.conv2d(images, 112, [7, 7],weights_initializer=trunc_normal(0.01),
            padding='VALID')
            current = slim.max_pool2d(current, [3, 3],stride=2)

            current = block(current,6,growth,scope='Conv2d_1')
            nchannels += 6
            current = transition(current,nchannels,scope='trans_1')

            current = block(current,12,growth,scope='Conv2d_2')
            nchannels += 12
            current = transition(current,nchannels,scope='trans_2')

            current = block(current,24,growth,scope='Conv2d_3')
            nchannels += 24
            current = transition(current,nchannels,scope='trans_3')

            current = block(current,16,growth,scope='Conv2d_4')
            nchannels += 16


            current = slim.avg_pool2d(current, current.shape[1:3],stride=[1, 1], padding='VALID',scope='pool_avg')
            current = slim.conv2d(current, num_classes, [1,1], activation_fn=tf.nn.softmax,weights_initializer=trunc_normal(0.001),scope='Conv2d_1x1')

            logits = tf.squeeze(current, [1, 2], name='SpatialSqueeze')
            end_points['Logits'] = logits
            ##########################

    return logits, end_points


def bn_drp_scope(is_training=True, keep_prob=0.8):
    keep_prob = keep_prob if is_training else 1
    with slim.arg_scope(
        [slim.batch_norm],
            scale=True, is_training=is_training, updates_collections=None):
        with slim.arg_scope(
            [slim.dropout],
                is_training=is_training, keep_prob=keep_prob) as bsc:
            return bsc


def densenet_arg_scope(weight_decay=0.004):
    """Defines the default densenet argument scope.

    Args:
      weight_decay: The weight decay to use for regularizing the model.

    Returns:
      An `arg_scope` to use for the inception v3 model.
    """
    with slim.arg_scope(
        [slim.conv2d],
        weights_initializer=tf.contrib.layers.variance_scaling_initializer(
            factor=2.0, mode='FAN_IN', uniform=False),
        activation_fn=None, biases_initializer=None, padding='same',
            stride=1) as sc:
        return sc


densenet.default_image_size = 224
