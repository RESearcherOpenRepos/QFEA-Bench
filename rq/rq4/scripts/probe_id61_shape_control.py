"""Container probe for the unchanged three-mode ID61 test fixture."""
import json
import os
import subprocess
import sys


def main():
    request = json.load(sys.stdin)
    os.chdir('/workspace/repo')
    subprocess.run(['git', 'checkout', '--force', request['base']], check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(['git', 'apply', '--whitespace=nowarn', '-'],
                   input=request['patch'].encode(), check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sys.path.insert(0, '/workspace/repo')
    import numpy as np
    from qiskit_nature.operators.second_quantization import QuadraticHamiltonian, FermionicOp

    m = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=complex)
    d = np.array([[0, 1j, 0], [-1j, 0, 1j], [0, -1j, 0]], dtype=complex)
    ham = QuadraticHamiltonian(m, d)
    w, energies, constant = ham.diagonalizing_bogoliubov_transform()
    result = {'shape': list(w.shape), 'energies': energies.tolist(),
              'constant': float(np.real(constant)), 'type': type(w).__name__}
    n = 3
    creation = [FermionicOp([(f'+_{j}', 1.0)], register_length=n,
                           display_format='sparse').to_matrix(sparse=False) for j in range(n)]
    annihilation = [a.conj().T for a in creation]
    identity = np.eye(2**n)
    original = np.zeros_like(identity, dtype=complex)
    for i in range(n):
        for j in range(n):
            original += m[i, j] * creation[i] @ annihilation[j]
            original += 0.5 * d[i, j] * creation[i] @ creation[j]
            original += 0.5 * d[i, j].conjugate() * annihilation[j] @ annihilation[i]
    result['original_spectrum'] = np.linalg.eigvalsh(original).tolist()
    if w.shape == (n, 2*n):
        u, v = w[:, :n], w[:, n:]
        result['car_identity_max_error'] = float(np.max(np.abs(w @ w.conj().T - np.eye(n))))
        result['car_pairing_max_error'] = float(np.max(np.abs(u @ v.T + v @ u.T)))
        full = np.block([[u, v], [v.conj(), u.conj()]])
        eye = np.eye(n)
        basis = np.block([[eye, eye], [1j*eye, -1j*eye]]) / np.sqrt(2)
        change = basis @ full @ basis.conj().T
        a, _ = ham.majorana_form()
        zero = np.zeros((n, n))
        expected = np.block([[zero, np.diag(energies)], [-np.diag(energies), zero]])
        result['canonical_max_error'] = float(np.max(np.abs(change @ a @ change.T - expected)))
        reconstructed = constant * identity.astype(complex)
        for row, energy in zip(w, energies):
            bdag = sum(row[j]*creation[j] + row[n+j]*annihilation[j] for j in range(n))
            reconstructed += energy * bdag @ bdag.conj().T
        result['reconstruction_max_error'] = float(np.max(np.abs(reconstructed - original)))
        result['reconstruction_equivalent'] = bool(np.allclose(reconstructed, original, atol=1e-7))
        result['reconstruction_hermitian'] = bool(np.allclose(reconstructed, reconstructed.conj().T))
        result['reconstructed_spectrum'] = np.linalg.eigvalsh(reconstructed).tolist()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
