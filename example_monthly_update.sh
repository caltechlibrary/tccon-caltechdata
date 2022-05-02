dc /data/tccon/3a-std-public

tar -czf tccon.latest.public.tgz *.public.qc.nc

export DATACITE=''
export RDMTOK=''

python update_all.py
python update_bit_record.py

