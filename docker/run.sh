#!/bin/bash

cd /checkouted

if [[ "${CONTINUOUS}" == true ]]; then
    python minefit.py --continuous --interval "${INTERVAL}"
else
    python minefit.py
fi