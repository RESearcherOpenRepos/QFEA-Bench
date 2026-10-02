"""Explicit source-reviewed decisions for IDs 107--119; no keyword classification.
Run from repository root. Groups below only share a decision after body review.
"""
import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
D={i:{} for i in range(107,120)}
def put(i, nums, label, lines, expected, rationale=None):
    if isinstance(nums,int): nums=[nums]
    if isinstance(lines,int): lines=[lines]
    for n in nums:
        assert n not in D[i]
        D[i][n]={'label':label,'assertions':[{'line':l,'expected':expected} for l in lines], 'rationale':rationale or expected}
Q='quantum_semantics/'; G='general_semantics/'; I='interface/'
put(107,1,Q+'circuit_decomposition',[186,187,202,203],'Optimized higher-order excitation circuits preserve the simulated quantum state (unit fidelity) and reduce depth against the Pauli reference.')
put(107,2,Q+'circuit_decomposition',93,'SWAP compiles to the specified three-CNOT circuit.')
put(107,range(3,7),Q+'circuit_decomposition',114,'Ry decomposition equals the specified Rz/Rx/Rz quantum gate sequence.')
put(107,range(7,12),Q+'circuit_decomposition',136,'Y-power decomposition equals the basis-rotated X-power gate sequence.')
put(107,range(12,15),Q+'circuit_decomposition',159,'Controlled-H decomposition equals the specified controlled rotation sequence.')
put(107,[15,16],I+'callable_execution',152,'For control=None this parameter case only calls compile_controlled_rotation without an exception; the assertion under if control is not None is not executed.','These two cases provide smoke coverage only, not a checked decomposition or fidelity invariant.')
put(108,1,Q+'circuit_translation_equivalence',77,'The GHZ preparation circuit has the explicitly specified 8x8 unitary, including amplitudes and signs.')
put(108,2,Q+'circuit_translation_equivalence',89,'ExpPauli matrix equals cos(-a/2) I + i sin(-a/2) (Y tensor X), checking angle, phase and tensor ordering.')
put(108,3,I+'wire_mapping_contract',[24,33,42,53],'Remapping wires returns gates with the requested control and target indices; no simulated state or unitary is compared.')
put(108,4,I+'input_format_equivalence',[71,80,82],'String, uppercase and integer axis arguments construct equal gate objects.')
put(108,5,Q+'state_preparation_correctness',148,'Elementary gate action agrees with symbolic reference quantum wavefunctions.')
put(108,6,I+'return_representation',[192,193,194,195,196],'Canonical moments expose the expected count, gates, targets and parameter values.')
put(108,7,I+'user_parameter_binding',[374,375,376],'Variable renaming preserves the expected old and new public variable lists.')
put(109,[1,2,3],Q+'ground_state_energy',[479,480],'PySCF FCI wavefunction agrees with the Hamiltonian ground eigenvector up to global phase and reproduces the FCI energy.')
put(109,4,Q+'ground_state_energy',140,'The active (last Python definition) test calls do_test_h2_hamiltonian with PySCF, checking the reference molecular spectrum.')
D[109][4]['assertions']=[{'line':146,'via_helper':140,'helper_selector':'tests/test_chemistry.py::do_test_h2_hamiltonian','expected':'H2 lowest eigenvalue equals -1.1368354639; helper also checks the excited spectrum.'}]
put(109,[5,6,7],Q+'hartree_fock_energy',[80,86],'Reference state has the expected Hartree-Fock energy, preserved by reordering the qubit encoding.')
put(110,1,I+'user_parameter_binding',[191,192,215,216],'Scalar and spin-resolved max_dim bound the alpha/beta CI dimensions to 10/10 and 15/10 respectively. Spin-square equivalence is also checked at 193/217.','Primary target is the new dimension-control parameter; record the secondary physical assertion without assigning two primary labels.')
put(110,2,G+'seed_reproducibility',[273,274,275,276],'Repeated runs with the same seed return identical energies, amplitudes and CI strings; the assertion is reproducibility, not a physical target value.')
put(110,3,G+'binary_integer_conversion',285,'Converting a 57-bit Boolean row to an integer preserves its binary digits.')
put(110,4,G+'binary_integer_conversion',294,'Converting a 64-bit Boolean row to an integer preserves its binary digits.')
put(111,1,Q+'ground_state_energy',158,'Boolean-array input yields the exact H2 CASCI total energy including nuclear repulsion.')
put(111,2,Q+'ground_state_energy',[124,125],'Selected CI reproduces the N2 reference energy and spin-square value.')
put(111,3,I+'user_parameter_binding',[229,230,253,254],'max_dim controls spin-resolved CI dimensions; spin-square is a secondary assertion at 231/255, consistently with ID110.')
put(111,4,Q+'hamiltonian_domain_validity',290,'All-zero occupation strings are invalid for the specified nonzero electron sector and must be rejected unless occupancy-based recovery is enabled.','The rejected condition is physical electron-number admissibility, not merely an input type or array shape.')
put(111,5,G+'binary_integer_conversion',384,'57-bit Boolean-to-integer conversion preserves every binary digit.')
put(111,6,G+'binary_integer_conversion',393,'64-bit Boolean-to-integer conversion preserves every binary digit.')
put(112,1,I+'return_representation',45,'Conversion returns an instance of the public QUBO class.')
put(112,2,G+'maxcut_model_formulation',76,'The Docplex MaxCut conversion gives the expected classical objective coefficients after the documented factor-of-two convention.')
put(112,3,I+'input_validation',36,'Mismatched term and coefficient counts raise ValueError; the companion valid construction exposes constant 3.')
put(112,4,G+'qubo_conversion',48,'Cleaning the polynomial terms returns the expected canonical term list.')
put(112,5,G+'symbolic_operator_arithmetic',56,'Duplicate polynomial terms have their numeric weights added correctly.')
put(112,6,G+'maxcut_model_formulation',[175,176,177],'MaxCut classical quadratic objective matches graph edges, weights and zero constant.')
put(112,7,G+'qubo_conversion',[122,123,124],'Number-partitioning quadratic objective has the expected terms, coefficients and constant.')
put(113,[1,2,3],G+'model_training_state',[65,66,67],'Fitting returns optimal parameters, an optimizer and fitted state; no quantum target value is asserted.')
put(113,[4,5],G+'model_training_state',[85,86,87],'Fitting initializes learned parameters and fitted state for the classifier.')
put(113,[6,7],I+'output_shape',[77,78],'Predictions have the reference array shape and ndarray type; no prediction values are asserted.')
put(113,[8,9],I+'user_parameter_binding',[108,109],'set_params exposes the requested qubit count and regularization choice and allows subsequent fitting.')
put(113,[10,11],I+'user_parameter_binding',126,'set_params changes exposed circuit depth to four layers and fitting remains callable.')
put(114,[1,2,3],G+'cross_entropy_loss',31,'Cross-entropy scalar loss equals the ordinary numerical reference for the supplied outputs and targets.')
put(114,[4,5,6],G+'batched_loss_gradient',[67],'Cross-entropy gradients for model parameters match the supplied classical chain-rule references.')
put(114,7,G+'model_training_state',[76,77,78],'Fitting changes learned model/observable parameters and marks the classifier fitted.')
put(114,8,G+'model_training_state',[105,106,107],'Two-output fitting updates learned parameters and fitted state.')
put(114,9,G+'decision_score_consistency',189,'Classifier decodes the fixed predictions into the expected all-one class labels; the asserted target is a decision output.')
put(114,10,G+'model_training_state',[77,78,79],'Regressor fitting changes learned parameters and marks the estimator fitted.')
put(114,11,Q+'observable_expectation_value',187,'Fixed ChebyshevRx circuit and SummedPaulis observable parameters yield the specified numerical expectation predictions.')
put(115,1,Q+'circuit_translation_equivalence',[67,73,78],'Gate-map and Hamiltonian mixer representations produce equivalent single/two-qubit rotation gates and coefficients.')
put(115,2,I+'input_validation',112,'A coefficient list with incompatible length raises ValueError; the message assertion inside the raises block is unreachable after the expected exception.')
put(115,3,Q+'circuit_translation_equivalence',[131,139,146,156],'RX/RXX and XY mixer terms map to the expected rotation gates, order and strengths.')
put(115,4,Q+'hamiltonian_representation_equivalence',[485,487,518,520],'Hamiltonian construction preserves Pauli terms, coefficients and identity contributions during register relabeling.')
put(115,5,I+'container_length',735,'The public length is the number of exposed linear and quadratic terms.')
put(115,6,I+'wire_mapping_contract',587,'qureg exposes the expected consecutive wire indices.')
put(115,7,I+'string_representation',781,'Symbolic expression uses the expected public formatting and symbols.')
put(115,8,Q+'hamiltonian_representation_equivalence',[632,633,635,636,638],'Partitioning Hamiltonian terms into one- and two-qubit terms preserves their coefficients and identity offset.')
put(115,9,Q+'qubit_operator_conversion',219,'Pauli tensor-product matrices match explicit complex entries, including Y phases and tensor ordering.')
put(116,1,Q+'hamiltonian_representation_equivalence',1382,'Hamiltonian sparse matrix equals the explicit 16x16 complex matrix for mixed Pauli terms.')
put(116,2,Q+'hamiltonian_representation_equivalence',[640,646,682,688],'Hamiltonian construction preserves Pauli coefficients and identity offsets when compacting wire indices.')
put(116,3,I+'wire_mapping_contract',766,'qureg exposes the expected consecutive wire indices.')
put(116,4,Q+'hamiltonian_representation_equivalence',[810,813,816,819,822],'Linear/quadratic Pauli partition preserves all terms, coefficients and identity offset.')
put(116,5,I+'string_representation',884,'Hamiltonian string has the exact documented ordering, coefficient and index formatting.')
put(116,6,I+'container_length',928,'Hamiltonian length equals the number of exposed polynomial terms.')
put(116,7,I+'string_representation',976,'Symbolic expression equals the expected externally exposed symbols.')
put(116,8,G+'operator_addition',[1056,1059],'Adding the two same-basis symbolic sums combines duplicate coefficients and constants; no Pauli multiplication law is needed.')
put(116,9,Q+'spin_operator_algebra',[1118,1167,1170,1173],'Squaring the Hamiltonian preserves Pauli multiplication signs, in particular XX times YY contributes negative ZZ.')
put(116,10,I+'return_representation',[1285,1309,1313],'hamiltonian_dict exposes the specified index-keyed or Pauli-keyed dictionary according to its classical flag.')
put(116,11,Q+'qubit_operator_conversion',285,'Tensor-product Pauli matrices equal the explicit complex reference matrices.')
for n,l in enumerate([84,149,54,97,71,76,127,113,127,118,70],1):
    put(117,n,G+'model_training_performance',l,'After inferred feature dimension, regression reproduces training targets within the stated tolerance; no independent quantum state or circuit value is asserted.')
for ns,ls in [([12,13],[138,139]),([14,15],[111,112]),([16,17],[116,117])]:
    put(117,ns,I+'output_shape',ls,'With feature count omitted, predictions retain the expected array type and shape.')
put(117,[18,19],G+'decision_score_consistency',146,'After dimension inference and fitting, classifier predictions equal the training labels.')
put(117,[20,21],G+'decision_score_consistency',143,'After dimension inference and fitting, classifier predictions equal the training labels.')
put(117,22,G+'model_training_performance',285,'The layered-circuit regressor learns the given targets after inferring input dimension.')
for n,l in enumerate([298,91,156,61,104,83,133,120,134,125,77],23):
    put(117,n,I+'input_validation',l,'An explicitly configured feature count inconsistent with the supplied vector raises ValueError; this checks the public input contract.')
put(117,[34,35],I+'output_shape',[97,98],'Existing QKRR predictions retain array type and shape.')
put(117,36,I+'estimator_lifecycle',64,'Predicting with an unfitted estimator raises the documented RuntimeError.')
for n,ls in [(1,[83,84,85]),(2,[98,100,101]),(3,[114,115,116,117]),(4,[130,131,132,133]),(5,[146,147,148,149])]:
    put(118,n,I+'user_parameter_binding',ls,'set_params propagates requested configuration values to exposed feature-map, observable and internal QNN attributes; no physical output is asserted.')
put(118,6,G+'model_training_state',[142,143,144],'After changing depth, refitting updates learned arrays and fitted state.')
put(118,7,G+'model_training_state',[138,139,140],'After changing depth, refitting updates learned arrays and fitted state.')
put(118,8,I+'estimator_lifecycle',[50,52,53],'Unfitted regressor emits the documented warning while returning an array of the expected shape.')
put(118,9,I+'estimator_lifecycle',49,'Unfitted classifier rejects prediction with the documented RuntimeError.')
put(118,10,G+'model_training_state',[65,66,67],'Fitting sets fitted state and updates both learned parameter arrays.')
put(118,11,G+'model_training_state',[62,63,64],'Fitting sets fitted state and updates both learned parameter arrays.')
for ns,ls in [(range(1,4),[236,242,243]),(range(4,7),[235,241,242]),([7,8],[240,244]),(range(9,12),[82]),(range(12,15),[89]),([15,16],[264,268]),([17,18],[277,281]),([19,20],[267,271]),([21,22],[265,269])]:
    put(119,ns,G+'model_serialization_preservation',ls,'Dump/load preserves learned model predictions (and, where asserted, learned parameters and refitting behavior).','Primary requirement is model persistence: comparisons are before/after serialization, without an independently specified physical invariant or quantum reference result. Backend fixtures do not by themselves make persistence quantum-specific.')
put(119,23,I+'serialization_contract',[35,36],'The serialized holder retains an executor attribute but strips its live executor value.')
put(119,24,I+'serialization_contract',[50,51],'Loading injects the exact supplied executor object.')
put(119,25,I+'serialization_contract',[69,70,76,77],'All nested executor references are removed on dump and replaced by the same supplied executor on load.')
put(119,26,I+'input_validation',[81,83,85],'Invalid load/dump source or target arguments raise TypeError.')
put(119,27,G+'model_training_state',[112,113,114],'Two-output fitting sets fitted state and updates both learned arrays.')
put(119,28,G+'warm_start_optimization_state',[132,133],'Full fitting is reproducible from initialization while partial_fit continues learned parameters.')
put(119,[29,30],I+'output_shape',[98,99],'QKRR prediction array type and shape remain compatible.')
for i,d in D.items():
    assert sorted(d)==list(range(1,len(d)+1))
    payload={'rationale':'Test bodies and referenced helpers at the exact patched commit were reviewed individually against the existing primary-assertion protocol. Setup and quantum repository membership do not determine the label. Parametrized cases retain distinct selectors.', 'decisions':[d[n] for n in sorted(d)], 'review_provenance': {'reviewer':'Codex','method':'Individual source-assertion review under existing protocol; explicit saved decisions, not automatic keyword classification.','date':'2026-10-02','human_agreement':'Author confirmation is recorded separately; these evidence records do not simulate three independent human votes.'}}
    out=Path(__file__).parent/f'{i:03d}_decisions.json';out.write_text(json.dumps(payload,indent=2)+'\n')
    if '--write' in sys.argv:
        subprocess.run([sys.executable,str(ROOT/'rq/rq3/scripts/write_constraint_annotation.py'),str(i)],input=json.dumps(payload),text=True,check=True,cwd=ROOT)
