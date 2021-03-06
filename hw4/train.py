import argparse
import os
import logging
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(levelname).1s %(asctime)s [%(name)s] %(message)s', '%H:%M:%S'
)
handler.setFormatter(formatter)
logging.basicConfig(level=logging.DEBUG, handlers=[handler])
logger = logging.getLogger(__name__)

import data, model
from gan import WassersteinGAN

def parse_arguments():
    parser = argparse.ArgumentParser('HW4')
    parser.add_argument('--gpus', type=str, default='0')
    parser.add_argument('--epochs', type=int, default=300)
    parser.add_argument('--batch_size', type=int, default=64)
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()

    os.environ['CUDA_VISIBLE_DEVICES'] = args.gpus

    data_sampler = data.DataSampler(os.path.join('data', 'tags.csv'))
    noise_sampler = data.NoiseSampler()
    g_net = model.Generator()
    d_net = model.Discriminator()

    wgan = WassersteinGAN(g_net, d_net, data_sampler, noise_sampler)
    wgan.train(epochs=args.epochs, batch_size=args.batch_size)
