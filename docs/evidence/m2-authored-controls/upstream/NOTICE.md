# Source metadata attribution

Experiment43's `source-layouts.json` extracts joint names and parents from NVIDIA Kimodo `kimodo/skeleton/definitions.py`, revision `58e781898b3d7e328a676a75d3e338c45dce3ad9`. Its exact source header is:

```text
SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0
```

The extraction retains names/hierarchy. The experiment separately authors rest transforms and motion controls; those transforms are not official SOMA calibration. See [experiment43](../../../../experiments/43-rig-mapping/REPORT.md).

Experiment41's `source-skeleton.json` extracts ordered names, parents and rest metadata from `src/skeleton.hpp` in the Apache-2.0 kimodo.cpp port, revision `5679ff19ba0a522c0b0516e9a9d402fe1af2c027`. It contains no model motion samples. See [experiment41](../../../../experiments/41-real-short-motion/REPORT.md). Both extractions are identified transformations of the pinned source metadata.

The exact supplied [official license](kimodo-LICENSE.txt), [C++ port license](kimodo-cpp-LICENSE.txt) and [verification receipt](receipt.json) are preserved here. The parent verified the official pinned license Git blob and actual NVIDIA header; this integration made no new fetch. This source-notice preservation is scoped to these published metadata derivatives. Code, model weights and the original CC0 fixture retain separate terms. It does not grant weight redistribution approval or close #10's complete distribution audit.
