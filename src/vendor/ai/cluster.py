import logging

import hdbscan
import numpy as np
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ClusterMeta(BaseModel):
    n_samples: int
    n_clusters: int
    n_noise: int
    noise_ratio: float
    min_cluster_size: int
    min_samples: int


def cluster_embeddings(*, embeddings: np.ndarray):
    if embeddings.ndim != 2:
        raise ValueError(f"embeddings must be 2D array (n_samples, dim), got {embeddings.shape}")

    n_samples, dim = embeddings.shape
    logger.info(f"Clustering {n_samples} embeddings (dim={dim}) with HDBSCAN")

    # Normalize embeddings
    # L2 normalization ensures that Euclidean distance is equivalent
    # to cosine distance, which is more appropriate for semantic embeddings.
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)  # avoid division by zero
    embeddings = embeddings / norms

    # HDBSCAN hyperparameters
    # min_cluster_size:
    #   Minimum number of samples required to form a cluster.
    #   We scale this with dataset size to avoid overly small clusters.
    min_cluster_size = max(4, int(0.04 * n_samples))

    # min_samples:
    #   Controls how conservative the clustering is.
    #   Setting it equal to min_cluster_size enforces stronger density
    #   requirements and prevents unrelated items from being merged.
    min_samples = min_cluster_size

    # Distance metric:
    #   Euclidean is used because embeddings are normalized.
    metric = "euclidean"

    # Cluster selection method:
    #   'eom' (Excess of Mass) favors larger, more stable clusters
    #   over very fine-grained, fragmented ones.
    method = "eom"

    logger.info(f"HDBSCAN params | min_cluster_size={min_cluster_size} min_samples={min_samples} metric={metric} method={method}")

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        # We are using euclidean distance because we have normalized the embeddings.
        # If we were not normalizing the embeddings, we would use cosine distance.
        metric=metric,
        cluster_selection_method=method,
    )

    labels = clusterer.fit_predict(embeddings)

    n_noise = int(np.sum(labels == -1))
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)

    meta = ClusterMeta(
        n_samples=n_samples,
        n_clusters=n_clusters,
        n_noise=n_noise,
        noise_ratio=n_noise / n_samples,
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
    )

    logger.info(f"✓ clusters={n_clusters} | noise={n_noise} ({(meta.noise_ratio * 100):.1f}%)")
    return labels, meta
