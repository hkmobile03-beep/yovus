"""Greedy online clustering of face embeddings into persistent identities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np

from .detector import DetectedFace


@dataclass
class Identity:
    """One person that appears in the video.

    ``faces`` accumulates every DetectedFace assigned to this identity. The
    ``best_face`` is the one with the largest area (biggest, most useful
    thumbnail for user preview).
    """

    index: int
    centroid: np.ndarray           # L2-normalized mean embedding
    faces: List[DetectedFace] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.faces)

    @property
    def best_face(self) -> DetectedFace:
        return max(self.faces, key=lambda f: f.area * f.det_score)

    def add(self, face: DetectedFace) -> None:
        n = len(self.faces)
        self.centroid = (self.centroid * n + face.embedding) / (n + 1)
        norm = np.linalg.norm(self.centroid)
        if norm > 0:
            self.centroid = self.centroid / norm
        self.faces.append(face)


def cluster_identities(
    faces: List[DetectedFace],
    similarity_threshold: float = 0.45,
) -> List[Identity]:
    """Greedy clustering: assign each face to the most-similar existing
    identity if cosine similarity >= threshold, else spawn a new identity.

    A threshold of ~0.45 works well for InsightFace buffalo_l embeddings.
    Lower = more merging (more forgiving), higher = stricter separation.
    """
    identities: List[Identity] = []
    for face in faces:
        if face.embedding is None:
            continue
        best_idx = -1
        best_sim = -1.0
        for i, ident in enumerate(identities):
            sim = float(np.dot(ident.centroid, face.embedding))
            if sim > best_sim:
                best_sim = sim
                best_idx = i
        if best_idx >= 0 and best_sim >= similarity_threshold:
            identities[best_idx].add(face)
        else:
            identities.append(
                Identity(
                    index=len(identities),
                    centroid=face.embedding.copy(),
                    faces=[face],
                )
            )
    # Sort by prominence (how often the identity appears) — most common first.
    identities.sort(key=lambda i: i.count, reverse=True)
    # Re-index after sort so preview folders line up with display order.
    for new_idx, ident in enumerate(identities):
        ident.index = new_idx
    return identities
