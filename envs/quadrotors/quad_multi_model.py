import torch
from torch import nn

from algorithms.appo.model_utils import get_obs_shape, nonlinearity, create_standard_encoder, EncoderBase, \
    register_custom_encoder
from algorithms.utils.pytorch_utils import calc_num_elements


class QuadMultiMeanEncoder(EncoderBase):
    # Mean embedding encoder based on the DeepRL for Swarms Paper
    def __init__(self, cfg, obs_space, timing, self_obs_dim=18, neighbor_obs_dim=6, neighbor_hidden_size=32):
        super().__init__(cfg, timing)
        self.self_obs_dim = self_obs_dim
        self.neighbor_obs_dim = neighbor_obs_dim
        self.neighbor_hidden_size = neighbor_hidden_size

        fc_encoder_layer = cfg.hidden_size
        # encode the current drone's observations
        self.self_encoder = nn.Sequential(
            nn.Linear(self.self_obs_dim, fc_encoder_layer),
            nonlinearity(cfg),
            nn.Linear(fc_encoder_layer, fc_encoder_layer),
            nonlinearity(cfg)
        )
        # encode the neighboring drone's observations
        self.neighbor_encoder = nn.Sequential(
            nn.Linear(self.neighbor_obs_dim, self.neighbor_hidden_size),
            nonlinearity(cfg),
        )
        self.self_encoder_out_size = calc_num_elements(self.self_encoder, (self.self_obs_dim,))
        self.neighbor_encoder_out_size = calc_num_elements(self.neighbor_encoder, (self.neighbor_obs_dim,))

        # Feed forward self obs and neighbor obs after concatenation
        self.feed_forward = nn.Linear(self.self_encoder_out_size + self.neighbor_encoder_out_size, cfg.hidden_size)

        self.init_fc_blocks(cfg.hidden_size)



    def forward(self, obs_dict):
        obs = obs_dict['obs']
        obs_self, obs_neighbors = obs[:, :self.self_obs_dim], obs[:, self.self_obs_dim:]
        self_embed = self.self_encoder(obs_self)
        obs_neighbors = torch.stack(torch.split(obs_neighbors, self.neighbor_obs_dim, dim=1))
        neighbor_embeds = self.neighbor_encoder(obs_neighbors)
        mean_embed = torch.mean(neighbor_embeds, 0)
        embeddings = torch.cat((self_embed, mean_embed), dim=1)
        out = self.feed_forward(embeddings)
        return out


def register_models():
    register_custom_encoder('quad_multi_encoder', QuadMultiMeanEncoder)
