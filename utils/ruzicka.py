import numpy as np
from scipy.optimize import minimize_scalar


def ruzicka_similarity(A, B):
    """
    Compute the Ruzicka similarity between two arrays A and B.
    """
    return np.sum(np.minimum(A, B)) / np.sum(np.maximum(A, B))


def scaled_ruzicka_similarity(k, A, B):
    """
    Compute the Ruzicka similarity with a scaling factor k applied to B.
    """
    B_scaled = k * B
    return -ruzicka_similarity(A, B_scaled)  # Negative because we want to maximize


def optimize_scaling(A, B):
    """
    Find the optimal scaling factor k that maximizes the Ruzicka similarity.
    """
    result = minimize_scalar(
        scaled_ruzicka_similarity, args=(A, B), bounds=(0, 10), method="bounded"
    )
    return result.x


# Example data
A = np.array([5, 3, 8])
B = np.array([4, 3, 6])

# Step 1: Find optimal scaling factor
optimal_k = optimize_scaling(A, B)

# Step 2: Scale dataset B using the optimal k
B_scaled = optimal_k * B

# Step 3: Compute new Ruzicka similarity
new_similarity = ruzicka_similarity(A, B_scaled)

print(f"Optimal scaling factor: {optimal_k:.4f}")
print(f"New Ruzicka similarity: {new_similarity:.4f}")
print(f"Scaled B: {B_scaled}")
