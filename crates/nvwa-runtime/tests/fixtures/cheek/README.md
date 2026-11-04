# Original cheek source witnesses

These four texts are exact gzip expansions of the CC0 MPFB 2.0.18 originals at
commit `d0a32e57a7f915cb2f2b95410e2117648c7bbb7e`. The matching gzip originals,
compressed and expanded hashes, license, and upstream paths are retained under
`assets/characters/mpfb-b1-v3/provenance/`. These test witnesses are independent
of the two derived bilateral runtime target files and their catalogue.

`b1_contour_tests.rs` pins each expanded SHA256, parses these original rows,
rejects overlapping left/right IDs, and computes expected signed unit conversion
for source vertices. No derived output or production target parser computes the
expectation. All original bytes, including zero rows and numeric spellings, stay
unchanged.
