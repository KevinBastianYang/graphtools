from __future__ import print_function
from load_tests import (
    graphtools,
    np,
    pd,
    pygsp,
    nose2,
    data,
    digits,
    build_graph,
    generate_swiss_roll,
    assert_raises,
    raises,
    warns,
    cdist,
)
from scipy.linalg import norm


#####################################################
# Check parameters
#####################################################


@raises(ValueError)
def test_sample_idx_and_precomputed():
    build_graph(data, n_pca=None,
                sample_idx=np.arange(10),
                precomputed='distance')


@raises(ValueError)
def test_sample_idx_wrong_length():
    build_graph(data, graphtype='mnn',
                sample_idx=np.arange(10))


@raises(ValueError)
def test_sample_idx_unique():
    build_graph(data, graph_class=graphtools.graphs.MNNGraph,
                sample_idx=np.ones(len(data)))


@raises(ValueError)
def test_sample_idx_none():
    build_graph(data, graphtype='mnn', sample_idx=None)


@raises(ValueError)
def test_build_mnn_with_precomputed():
    build_graph(data, n_pca=None, graphtype='mnn', precomputed='distance')


@raises(ValueError)
def test_mnn_with_square_theta_wrong_length():
    n_sample = len(np.unique(digits['target']))
    # square matrix theta of the wrong size
    build_graph(
        data, thresh=0, n_pca=20,
        decay=10, knn=5, random_state=42,
        sample_idx=digits['target'],
        kernel_symm='theta',
        theta=np.tile(np.linspace(0, 1, n_sample - 1),
                      n_sample).reshape(n_sample - 1, n_sample))


@raises(ValueError)
def test_mnn_with_vector_theta():
    n_sample = len(np.unique(digits['target']))
    # vector theta
    build_graph(
        data, thresh=0, n_pca=20,
        decay=10, knn=5, random_state=42,
        sample_idx=digits['target'],
        kernel_symm='theta',
        theta=np.linspace(0, 1, n_sample - 1))


@raises(ValueError)
def test_mnn_with_unbounded_theta():
    build_graph(
        data, thresh=0, n_pca=20,
        decay=10, knn=5, random_state=42,
        sample_idx=digits['target'],
        kernel_symm='theta',
        theta=2)


@raises(ValueError)
def test_mnn_with_string_theta():
    build_graph(
        data, thresh=0, n_pca=20,
        decay=10, knn=5, random_state=42,
        sample_idx=digits['target'],
        kernel_symm='theta',
        theta='invalid')


@warns(FutureWarning)
def test_mnn_with_gamma():
    build_graph(
        data, thresh=0, n_pca=20,
        decay=10, knn=5, random_state=42,
        sample_idx=digits['target'],
        kernel_symm='theta',
        gamma=0.9)


@warns(FutureWarning)
def test_mnn_with_kernel_symm_gamma():
    build_graph(
        data, thresh=0, n_pca=20,
        decay=10, knn=5, random_state=42,
        sample_idx=digits['target'],
        kernel_symm='gamma',
        theta=0.9)


@warns(UserWarning)
def test_mnn_with_theta_and_kernel_symm_not_theta():
    build_graph(
        data, thresh=0, n_pca=20,
        decay=10, knn=5, random_state=42,
        sample_idx=digits['target'],
        kernel_symm='+',
        theta=0.9)


@warns(UserWarning)
def test_mnn_with_kernel_symmm_theta_and_no_theta():
    build_graph(
        data, thresh=0, n_pca=20,
        decay=10, knn=5, random_state=42,
        sample_idx=digits['target'],
        kernel_symm='theta')


def test_mnn_with_non_zero_indexed_sample_idx():
    X, sample_idx = generate_swiss_roll()
    G = build_graph(X, sample_idx=sample_idx,
                    kernel_symm='theta', theta=0.5,
                    n_pca=None, use_pygsp=True)
    sample_idx += 1
    G2 = build_graph(X, sample_idx=sample_idx,
                     kernel_symm='theta', theta=0.5,
                     n_pca=None, use_pygsp=True)
    assert G.N == G2.N
    assert np.all(G.d == G2.d)
    assert (G.W != G2.W).nnz == 0
    assert (G2.W != G.W).sum() == 0
    assert isinstance(G2, graphtools.graphs.MNNGraph)


def test_mnn_with_string_sample_idx():
    X, sample_idx = generate_swiss_roll()
    G = build_graph(X, sample_idx=sample_idx,
                    kernel_symm='theta', theta=0.5,
                    n_pca=None, use_pygsp=True)
    sample_idx = np.where(sample_idx == 0, 'a', 'b')
    G2 = build_graph(X, sample_idx=sample_idx,
                     kernel_symm='theta', theta=0.5,
                     n_pca=None, use_pygsp=True)
    assert G.N == G2.N
    assert np.all(G.d == G2.d)
    assert (G.W != G2.W).nnz == 0
    assert (G2.W != G.W).sum() == 0
    assert isinstance(G2, graphtools.graphs.MNNGraph)


#####################################################
# Check kernel
#####################################################


def test_mnn_graph_float_theta():
    X, sample_idx = generate_swiss_roll()
    theta = 0.9
    k = 10
    a = 20
    metric = 'euclidean'
    beta = 0.5
    samples = np.unique(sample_idx)

    K = np.zeros((len(X), len(X)))
    K[:] = np.nan
    K = pd.DataFrame(K)

    for si in samples:
        X_i = X[sample_idx == si]            # get observations in sample i
        for sj in samples:
            X_j = X[sample_idx == sj]        # get observation in sample j
            pdx_ij = cdist(X_i, X_j, metric=metric)  # pairwise distances
            kdx_ij = np.sort(pdx_ij, axis=1)  # get kNN
            e_ij = kdx_ij[:, k]             # dist to kNN
            pdxe_ij = pdx_ij / e_ij[:, np.newaxis]  # normalize
            k_ij = np.exp(-1 * (pdxe_ij ** a))  # apply alpha-decaying kernel
            if si == sj:
                K.iloc[sample_idx == si, sample_idx == sj] = (
                    k_ij + k_ij.T) / 2
            else:
                # fill out values in K for NN on diagonal
                K.iloc[sample_idx == si, sample_idx == sj] = k_ij
    Kn = K.copy()
    for i in samples:
        curr_K = K.iloc[sample_idx == i, sample_idx == i]
        i_norm = norm(curr_K, 1, axis=1)
        for j in samples:
            if i == j:
                continue
            else:
                curr_K = K.iloc[sample_idx == i, sample_idx == j]
                curr_norm = norm(curr_K, 1, axis=1)
                scale = np.minimum(
                    np.ones(len(curr_norm)), i_norm / curr_norm) * beta
                Kn.iloc[sample_idx == i, sample_idx == j] = (
                    curr_K.T * scale).T

    K = Kn
    W = np.array((theta * np.minimum(K, K.T)) +
                 ((1 - theta) * np.maximum(K, K.T)))
    np.fill_diagonal(W, 0)
    G = pygsp.graphs.Graph(W)
    G2 = graphtools.Graph(X, knn=k + 1, decay=a, beta=beta,
                          kernel_symm='theta', theta=theta,
                          distance=metric, sample_idx=sample_idx, thresh=0,
                          use_pygsp=True)
    assert G.N == G2.N
    np.testing.assert_array_equal(G.dw, G2.dw)
    assert (G.W != G2.W).nnz == 0
    assert (G2.W != G.W).sum() == 0
    assert isinstance(G2, graphtools.graphs.MNNGraph)


def test_mnn_graph_matrix_theta():
    X, sample_idx = generate_swiss_roll()
    bs = 0.8
    theta = np.array([[1, bs],  # 0
                      [bs,  1]])  # 3
    k = 10
    a = 20
    metric = 'euclidean'
    beta = 0
    samples = np.unique(sample_idx)

    K = np.zeros((len(X), len(X)))
    K[:] = np.nan
    K = pd.DataFrame(K)

    for si in samples:
        X_i = X[sample_idx == si]            # get observations in sample i
        for sj in samples:
            X_j = X[sample_idx == sj]        # get observation in sample j
            pdx_ij = cdist(X_i, X_j, metric=metric)  # pairwise distances
            kdx_ij = np.sort(pdx_ij, axis=1)  # get kNN
            e_ij = kdx_ij[:, k]             # dist to kNN
            pdxe_ij = pdx_ij / e_ij[:, np.newaxis]  # normalize
            k_ij = np.exp(-1 * (pdxe_ij ** a))  # apply alpha-decaying kernel
            if si == sj:
                K.iloc[sample_idx == si, sample_idx == sj] = (
                    k_ij + k_ij.T) / 2
            else:
                # fill out values in K for NN on diagonal
                K.iloc[sample_idx == si, sample_idx == sj] = k_ij
    Kn = K.copy()
    for i in samples:
        curr_K = K.iloc[sample_idx == i, sample_idx == i]
        i_norm = norm(curr_K, 1, axis=1)
        for j in samples:
            if i == j:
                continue
            else:
                curr_K = K.iloc[sample_idx == i, sample_idx == j]
                curr_norm = norm(curr_K, 1, axis=1)
                scale = np.minimum(
                    np.ones(len(curr_norm)), i_norm / curr_norm) * beta
                Kn.iloc[sample_idx == i, sample_idx == j] = (
                    curr_K.T * scale).T

    K = Kn

    K = np.array(K)

    matrix_theta = pd.DataFrame(np.zeros((len(sample_idx), len(sample_idx))))
    for ix, si in enumerate(set(sample_idx)):
        for jx, sj in enumerate(set(sample_idx)):
            matrix_theta.iloc[sample_idx == si,
                              sample_idx == sj] = theta[ix, jx]

    W = np.array((matrix_theta * np.minimum(K, K.T)) +
                 ((1 - matrix_theta) * np.maximum(K, K.T)))
    np.fill_diagonal(W, 0)
    G = pygsp.graphs.Graph(W)
    G2 = graphtools.Graph(X, knn=k + 1, decay=a, beta=beta,
                          kernel_symm='theta', theta=theta,
                          distance=metric, sample_idx=sample_idx, thresh=0,
                          use_pygsp=True)
    assert G.N == G2.N
    np.testing.assert_array_equal(G.dw, G2.dw)
    assert (G.W != G2.W).nnz == 0
    assert (G2.W != G.W).sum() == 0
    assert isinstance(G2, graphtools.graphs.MNNGraph)


#####################################################
# Check interpolation
#####################################################


# TODO: add interpolation tests

def test_verbose():
    X, sample_idx = generate_swiss_roll()
    print()
    print("Verbose test: MNN")
    build_graph(X, sample_idx=sample_idx,
                kernel_symm='theta', theta=0.5,
                n_pca=None, verbose=True)


def test_set_params():
    X, sample_idx = generate_swiss_roll()
    G = build_graph(X, sample_idx=sample_idx,
                    kernel_symm='theta', theta=0.5,
                    n_pca=None,
                    thresh=1e-4)
    assert G.get_params() == {
        'n_pca': None,
        'random_state': 42,
        'kernel_symm': 'theta',
        'theta': 0.5,
        'beta': 1,
        'adaptive_k': None,
        'knn': 3,
        'decay': 10,
        'bandwidth': None,
        'distance': 'euclidean',
        'thresh': 1e-4,
        'n_jobs': 1
    }
    G.set_params(n_jobs=4)
    assert G.n_jobs == 4
    for graph in G.subgraphs:
        assert graph.n_jobs == 4
        assert graph.knn_tree.n_jobs == 4
    G.set_params(random_state=13)
    assert G.random_state == 13
    for graph in G.subgraphs:
        assert graph.random_state == 13
    G.set_params(verbose=2)
    assert G.verbose == 2
    for graph in G.subgraphs:
        assert graph.verbose == 2
    G.set_params(verbose=0)
    assert_raises(ValueError, G.set_params, knn=15)
    assert_raises(ValueError, G.set_params, decay=15)
    assert_raises(ValueError, G.set_params, distance='manhattan')
    assert_raises(ValueError, G.set_params, thresh=1e-3)
    assert_raises(ValueError, G.set_params, beta=0.2)
    assert_raises(ValueError, G.set_params, adaptive_k='min')
    G.set_params(knn=G.knn,
                 decay=G.decay,
                 thresh=G.thresh,
                 distance=G.distance,
                 beta=G.beta,
                 adaptive_k=G.adaptive_k)
