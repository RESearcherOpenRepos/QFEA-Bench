FROM benchmark-base:qiskit_nature_45_50

WORKDIR /workspace

ENV SAMPLE_ID=qiskit_nature_45_50
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/45
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/50
ENV BASE_COMMIT=41d31c17b8ee4d7dee5330ec5a230a8e1f3d18b2
ENV PATCHED_COMMIT=5355cdfa825d696404902c81e965b021667b70bc
ENV PR_HEAD_COMMIT=5355cdfa825d696404902c81e965b021667b70bc
ENV FAIL_PASS_TEST_PATHS="test/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_full_active_space test/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_minimal_active_space test/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_unpaired_electron_active_space test/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_arbitrary_active_orbitals test/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_active_space_for_q_molecule_v2"
ENV PASS_PASS_TEST_PATHS="test/drivers/hdf5d/test_driver_hdf5.py::TestDriverHDF5::test_driver_hf_energy test/drivers/hdf5d/test_driver_hdf5.py::TestDriverHDF5::test_driver_num_orbitals test/drivers/hdf5d/test_driver_hdf5.py::TestDriverHDF5::test_driver_mo_onee_ints test/drivers/hdf5d/test_driver_hdf5_save.py::TestDriverHDF5Save::test_driver_hf_energy test/drivers/hdf5d/test_driver_hdf5_save.py::TestDriverHDF5Save::test_driver_mo_onee_ints test/drivers/hdf5d/test_driver_hdf5_save.py::TestDriverHDF5Save::test_driver_mo_eri_ints"
ENV FAIL_PASS_EXTRA_FILES="test/transformers/__init__.py test/transformers/test_active_space_transformer.py test/transformers/BeH_sto3g.hdf5 test/transformers/H2_631g.hdf5 test/transformers/H2_sto3g.hdf5 test/transformers/H2_sto3g_v2.hdf5"

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
