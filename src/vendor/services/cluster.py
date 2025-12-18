from __future__ import annotations

import logging
from itertools import combinations

import numpy as np
from pydantic import BaseModel
from sklearn.metrics.pairwise import cosine_similarity

from src.db.models.product import Product
from src.vendor.ai.cluster import ClusterMeta, cluster_embeddings

logger = logging.getLogger(__name__)


# NOTE: These values are not configurable yet, but it could came from the database.
SIMILARITY_THRESHOLD = 0.7
BRAND_MATCH_BONUS = 0.03
CATEGORY_MATCH_BONUS = 0.1
NOISE_CLUSTER_LABEL = -1


class ClusterItem(BaseModel):
    product: Product

    model_config = {
        "arbitrary_types_allowed": True,
    }


class ClusterGroup(BaseModel):
    cluster_id: int
    items: list[ClusterItem]


def cluster_products(*, products: list[Product]) -> tuple[list[ClusterGroup], ClusterMeta]:
    embeddings = np.array([p.embedding for p in products])

    labels, meta = cluster_embeddings(embeddings=embeddings)

    clusters = map_cluster_result(products=products, labels=labels)
    # clusters = run_heuristic_grouping(clusters=clusters)

    return clusters, meta


def map_cluster_result(
    *,
    products: list[Product],
    labels: np.ndarray,
) -> list[ClusterGroup]:
    clusters: dict[int, list[ClusterItem]] = {}

    for product, label in zip(products, labels, strict=False):
        if label == NOISE_CLUSTER_LABEL:
            continue

        if label not in clusters:
            clusters[label] = []

        clusters[label].append(ClusterItem(product=product))

    return [ClusterGroup(cluster_id=cluster_id, items=items) for cluster_id, items in clusters.items()]


def run_heuristic_grouping(
    *,
    clusters: list[ClusterGroup],
) -> list[ClusterGroup]:
    """
    Refine HDBSCAN clusters using heuristic pairwise similarity.
    """
    refined_groups: list[ClusterGroup] = []

    for cluster in clusters:
        products = [item.product for item in cluster.items]

        if len(products) == 1:
            # Cluster unitário → já é um grupo válido
            refined_groups.append(cluster)
            continue

        heuristic_groups = _score_and_group(
            products=products,
            cluster_id=cluster.cluster_id,
        )

        for group in heuristic_groups:
            refined_groups += [
                ClusterGroup(
                    cluster_id=group["cluster_id"],
                    items=[
                        ClusterItem(
                            product=product,
                            probability=group["confidence"],
                        )
                        for product in group["products"]
                    ],
                )
            ]

    return refined_groups


def _score_and_group(
    *,
    products: list[Product],
    cluster_id: int,
):
    # Final list of groups generated for this cluster
    groups = []

    # Keep track of product IDs that were already assigned to a group
    # to avoid grouping the same product multiple times
    visited_product_ids = set()

    # Iterate through products, treating each one as an "anchor"
    for i, anchor_product in enumerate(products):
        # Skip products that were already grouped
        if anchor_product.id in visited_product_ids:
            continue

        # Start a new group with the anchor product
        group = [anchor_product]

        # Mark anchor product as visited
        visited_product_ids.add(anchor_product.id)

        # Compare the anchor product with the remaining products
        # (only those after the current index to avoid duplicate comparisons)
        for candidate_product in products[i + 1 :]:
            # Skip products that were already grouped
            if candidate_product.id in visited_product_ids:
                continue

            # Compute similarity score between anchor and candidate
            score = _pair_score(
                product1=anchor_product,
                product2=candidate_product,
            )

            # If similarity is above the threshold, add to the group
            if score >= SIMILARITY_THRESHOLD:
                group.append(candidate_product)
                visited_product_ids.add(candidate_product.id)

        # Calculate a confidence score for the whole group
        confidence = _calculate_group_confidence(group=group)

        # Append the resulting group with metadata
        groups.append({
            "cluster_id": cluster_id,
            "products": group,
            "confidence": confidence,
        })

    # Return all groups created for this cluster
    return groups


def _calculate_group_confidence(*, group: list[Product]) -> float:
    # If the group has only one product, confidence is maximal by definition
    if len(group) <= 1:
        return 1.0

    # Calculate pairwise similarity scores for all product combinations in the group
    pair_scores = [_pair_score(product1=p1, product2=p2) for p1, p2 in combinations(group, 2)]

    # Default strategy: average similarity across all pairs
    confidence = np.mean(pair_scores)

    # Ensure confidence stays within the valid range [0.0, 1.0]
    # (important because bonuses may push scores above 1.0)
    confidence = max(0.0, min(confidence, 1.0))

    # Round for consistency and readability
    return round(confidence, 4)


def _pair_score(*, product1: Product, product2: Product) -> float:
    """Calculate similarity score between two products."""

    # Compute semantic similarity using cosine similarity on embeddings
    semantic_similarity = cosine_similarity(
        [product1.embedding],
        [product2.embedding],
    )[0][0]

    # Base score starts as semantic similarity
    score = semantic_similarity

    # Add bonus if both products belong to the same brand
    if _match_brand(product1=product1, product2=product2):
        score += BRAND_MATCH_BONUS

    # Add bonus if both products belong to the same category
    if _match_category(product1=product1, product2=product2):
        score += CATEGORY_MATCH_BONUS

    # Round score for consistency
    return round(score, 4)


def _match_brand(*, product1: Product, product2: Product) -> bool:
    """Check if both products have the same brand."""

    # Return True only if both products have a brand and the brand IDs match
    return product1.brand_id is not None and product2.brand_id is not None and product1.brand_id == product2.brand_id


def _match_category(*, product1: Product, product2: Product) -> bool:
    """Check if both products have the same category."""

    # Return True only if both products have a category and the category IDs match
    return product1.category_id is not None and product2.category_id is not None and product1.category_id == product2.category_id
