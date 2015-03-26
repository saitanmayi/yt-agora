#!/bin/bash 
# Run Sunrise and generate CANDELized images
# 

# Set environment
source /project/projectdirs/agora/scripts/activate_yt-agora.sh

RUN_DIR=$(pwd)
export RUN_DIR=$RUN_DIR   # overwritten by setupSunriseRun.py if needed
export SUNRISE_DIR=$RUN_DIR/sunrise
export INPUT_DIR=$RUN_DIR/input
export OUTPUT_DIR=$RUN_DIR/output

export IMPRESSION=$IMPRESSION # overwritten by setupSunriseRun.py if needed
export BLACKBOX=$BLACKBOX # overwritten by setupSunriseRun.py if needed
export IDL_PATH=$AGORA_PIPE_INSTALL/packages/astron_idl/pro:$BLACKBOX:$IDL_PATH

SKIPCALZETTI=True
SKIPIDL=True
export SKIPCALZETTI=$SKIPCALZETTI # overwritten by setupSunriseRun.py if needed
export SKIPIDL=$SKIPIDL # overwritten by setupSunriseRun.py if needed

echo "Starting Sunrise run and CANDELization on $HOST at $RUN_DIR"

function test {
    "$@"
    status=$?
    if [ $status -ne 0 ]; then
        echo "error with $1, exiting"
        exit
    else
        echo "success"
    fi
    return $status
}

cd $INPUT_DIR
for i in *.config; 
    do cp $i `basename $i config`config-used; 
done
for i in *.stub; 
    do cp $i `basename $i stub`stub-used; 
done

cd $OUTPUT_DIR
rm *tmp*

# Run SFRHIST
if [ ! -f broadband.fits ]
    then
    echo 'No broadband found - running sfrhist'
    # modify star velocities
    echo "
import astropy.io.fits as pyfits
import numpy as np
file = \"$INPUT_DIR/initial.fits\"
pd,pdh = pyfits.getdata(file,'PARTICLEDATA',header=True)
dat = np.array(pd)
dat['velocity'][:,:]=0.0
pyfits.update(file,dat,header=pdh,ext=4,memmap=False)
print 'modified file velocity to zero'
    " > $INPUT_DIR/modvel.py
    python $INPUT_DIR/modvel.py
    test aprun -n 1 -d 24 $SUNRISE_DIR/src/sfrhist $INPUT_DIR/sfrhist.config 2>&1 > log-sfrhist 
    #cat log-sfrhist | grep -v 'SED with' | grep -v 'PDR radius' | grep -v 'SED el'
else
    echo 'sfrhist.fits found - skipping sfrhist'
fi

# Run MCRX
echo 'starting MCRX'
free -lmt -s5 | tee -a log-memsample >> log-mcrx-mem &
test aprun -n 1 -d 24 $SUNRISE_DIR/src/mcrx $INPUT_DIR/mcrx.config 2>&1 | tee -a log-mcrx > log-mcrx-mem
echo 'finished MCRX'
pkill -9 free

# Make an aux.fits file
cp mcrx.fits aux.fits
echo "
import astropy.io.fits as pf
import numpy as np

fh=pf.open('mcrx.fits')
cams = fh['MCRX'].header['N_CAMERA']

for i in range(cams):
    for ext in ['CAMERA%i','CAMERA%i-NONSCATTER']:
        extname=ext%i
        print extname
        try:
            img,h = pf.getdata('aux.fits',extname,header=True)
            pf.update('aux.fits',np.ones((2,2),dtype='f8'),extname=extname,header=h)
        except:
            pass
extname='GRIDSTRUCTURE'
img,h = pf.getdata('aux.fits',extname,header=True)
dat = np.ones(1,dtype=img.dtype)
pf.update('aux.fits',dat,extname=extname,header=h)
" > aux.py
sleep 1
python aux.py
rm aux.py

rm mcrx-*.fits

# Applied Calzetti attenuation
if [ "$SKIPCALZETTI" != "True" ]
then
    echo "Starting calzetti process"
    seq 0.0 0.07 0.35 | parallel -j1 -u "echo calzetti {}; python  $IMPRESSION/export/input/mcrx_calzetti.py mcrx.fits {} mcrx-{}.fits"
    # wait for mcrx calzetti processes  to finish
    wait

    while [ $(ps -aef | grep mcrx_calzetti.py | grep -v grep | wc -l) != "0" ]; 
    do 
        echo "On host $HOST, not done with mcrx calzetti, jobs left" $( ps -aef | grep mcrx_calzetti | grep -v grep | wc -l ) 
        sleep 10;
    done 

    echo "finished mcrx calzetti"
fi

# Run BROADBAND
echo 'Starting BROADBANDs'
($SUNRISE_DIR/src/broadband $INPUT_DIR/broadband.config 2>&1 >log-broadband &)
($SUNRISE_DIR/src/broadband $INPUT_DIR/broadbandz.config 2>&1 >log-broadbandz &)
echo spawned normal broadbands
for bv in 0.07 0.14 0.21 0.28 0.35
do
    echo "spawning broadband calzetti: $bv"
    sed "s/mcrx.fits/mcrx-$bv.fits/g" $INPUT_DIR/broadband.config > $INPUT_DIR/broadband-$bv.config
    sed -i "s/broadband.fits/broadband-$bv.fits/g" $INPUT_DIR/broadband-$bv.config  
    sed "s/mcrx.fits/mcrx-$bv.fits/g" $INPUT_DIR/broadbandz.config > $INPUT_DIR/broadbandz-$bv.config
    sed -i "s/broadbandz.fits/broadbandz-$bv.fits/g" $INPUT_DIR/broadbandz-$bv.config 
    ($SUNRISE_DIR/src/broadband $INPUT_DIR/broadband-$bv.config 2>&1 >log-broadband-$bv &)
    ($SUNRISE_DIR/src/broadband $INPUT_DIR/broadbandz-$bv.config 2>&1 >log-broadbandz-$bv &)
done

while [ $(ps -aef | grep broadband | grep -v grep | wc -l) != "0" ]; 
do 
    echo "On host $HOST, not done with broadband, jobs left " $(ps -aef | grep broadband | grep -v grep | wc -l ) 
    sleep 10;
done 

echo "Finished BROADBANDSs"
    
# Get easy access to FITS headers
echo "
import glob
import astropy.io.fits as pyfits

for f in glob.glob('*fits') + glob.glob('../input/*fits'):
    try:
        print '****   FILE ', f
        print ' '
        fh = pyfits.open(f)
        for x in fh:
            for k,v in x._header.items():
                print k,v
        print ' '
        
    except:
        continue " > temp.py

python temp.py > data-fits_headers
rm temp.py

# Run the blackbox
if [ "$SKIPIDL" != "True" ]
then
    module load idl
    cd $BLACKBOX
    ls $OUTPUT_DIR/broadbandz*fits | sort > sim_filenames.cat 
    timeout3 -t 1800 -d 10 -i 10 idl $BLACKBOX/sim_call.pro -queue
    cd $OUTPUT_DIR
    tar -zcvf images.tar.gz images/
fi

# Make the RGB images and tar them up
python $IMPRESSION/plot/plot_rgb.py $OUTPUT_DIR/broadband.fits
tar -zcvf rgb.tar.gz CAMERA*png

python $IMPRESSION/plot/plot_broadbands.py sed $OUTPUT_DIR/broadband.fits 
#mv sed*png sed.png

export f2png= $IMPRESSION/plot/plot_candelsized.py
python $f2png $OUTPUT_DIR/images/broadbandz_CAMERA0-BROADBAND_F606W_candelized_noise.fits cam0_v.png -1 "V "
python $f2png $OUTPUT_DIR/images/broadbandz_CAMERA1-BROADBAND_F606W_candelized_noise.fits cam1_v.png -1 "V "
python $f2png $OUTPUT_DIR/images/broadbandz_CAMERA0-BROADBAND_F125W_candelized_noise.fits cam0_j.png -1 "J "
python $f2png $OUTPUT_DIR/images/broadbandz_CAMERA1-BROADBAND_F125W_candelized_noise.fits cam1_j.png -1 "J "
python $f2png $OUTPUT_DIR/images/broadbandz_CAMERA0-BROADBAND_F160W_candelized_noise.fits cam0_h.png -1 "H "
python $f2png $OUTPUT_DIR/images/broadbandz_CAMERA1-BROADBAND_F160W_candelized_noise.fits cam1_h.png -1 "H "
python $f2png $OUTPUT_DIR/images/broadbandz_CAMERA0-BROADBAND_F850LP_candelized_noise.fits cam0_z.png -1 "z "
python $f2png $OUTPUT_DIR/images/broadbandz_CAMERA1-BROADBAND_F850LP_candelized_noise.fits cam1_z.png -1 "z "

#trim the info file
#python $IMPRESSION/plot/plot_info_file.py ../sync/*.info rowd.png

# Coalesce the composite image
module load imagemagick
cd $OUTPUT_DIR/images
convert +append CAMERA0-BROADBAND_blur.png CAMERA1-BROADBAND_blur.png -resize 400x800 rowa.png
convert +append cam0_v.png cam0_z.png cam1_v.png cam1_z.png rowb.png
convert +append cam0_j.png cam0_h.png cam1_j.png cam1_h.png rowc.png
convert -append rowa.png rowa2.png rowb.png rowc.png rowd.png composite.png
echo "
fn=\"$FULLNAME\"
scale = fn.split('_')[1].strip().strip('a')
z=1.0/float(scale)-1 
print '%1.1f'%z  
" > tmp.py
export ZF=$(python tmp.py)
rm tmp.py

export NUV0=$(python $IMPRESSION/scripts/extract_mag.py broadband.fits nuv 0 )
export U0=$(python $IMPRESSION/scripts/extract_mag.py broadband.fits bessel_u 0 )
export V0=$(python $IMPRESSION/scripts/extract_mag.py broadband.fits bessel_v 0 )
export J0=$(python $IMPRESSION/scripts/extract_mag.py broadband.fits wfcam_j 0 )
export z0=$(python $IMPRESSION/scripts/extract_mag.py broadband.fits wfcam_z 0 )
export NUV1=$(python $IMPRESSION/scripts/extract_mag.py broadband.fits nuv 1 )
export U1=$(python $IMPRESSION/scripts/extract_mag.py broadband.fits bessel_u 1 )
export V1=$(python $IMPRESSION/scripts/extract_mag.py broadband.fits bessel_v 1 )
export J1=$(python $IMPRESSION/scripts/extract_mag.py broadband.fits wfcam_j 1 )
export z1=$(python $IMPRESSION/scripts/extract_mag.py broadband.fits wfcam_z 1 )
export TEXTa="$FULLNAME  z=$ZF"
export TEXT="$FULLNAME\nz=$ZF\nNUV=$NUV0\nU=$U0\nV=$V0\nJ=$J0\nz=$z0" 
export TEXT2="\n\nNUV=$NUV1\nU=$U1\nV=$V1\nJ=$J1\nz=$z1" 
convert composite.png -gravity northwest \
    -stroke '#000C' -strokewidth 2 -annotate 0 "$TEXT" \
    -stroke none -fill white -annotate 0 "$TEXT" composite.png
convert composite.png -gravity northeast\
    -stroke '#000C' -strokewidth 2 -annotate 0 "$TEXT2" \
    -stroke none -fill white -annotate 0 "$TEXT2" composite.png

# Make theory composite
cd $OUTPUT_DIR
mkdir tempimg
cd $OUTPUT_DIR/tempimg
tar -zxvf ../../sync/*plots.tar.gz
convert -trim *gas_cam00*png
convert -trim *gas_cam01*png
convert -trim *dm_cam00*png
convert -trim *dm_cam01*png
convert -trim *dm_2_*png
convert -trim *phase_temp_gas*png
convert +append *gas_cam00*png *gas_cam01*png -resize 300x800 ../rowta.png
convert +append *dm_cam00*png *dm_cam01*png -resize 300x800 ../rowtb.png
convert +append *dm_2*png *phase_temp_gas*png -resize 300x800 ../rowtc.png
cd ..
rm -rdf tempimg
convert -append rowta.png rowtb.png rowtc.png compositeb.png
convert compositeb.png -gravity northwest -annotate 0 "$TEXTa" compositeb.png
convert compositeb.png -gravity northwest -annotate 0x0+30+9   "gas" compositeb.png
convert compositeb.png -gravity northwest -annotate 0x0+330+9  "gas" compositeb.png
convert compositeb.png -gravity northwest -annotate 0x0+30+290  "dark matter" compositeb.png
convert compositeb.png -gravity northwest -annotate 0x0+330+290 "dark matter" compositeb.png
convert compositeb.png -gravity northwest -annotate 0x0+30+570  "dark matter 2mpc comoving" compositeb.png
convert compositeb.png -gravity northwest -annotate 0x0+340+570 "gas phase" compositeb.png


#CLEAN UP

#now remove the CANDLS images and rgb images
#rm -rdf images
#rm CAMERA*png
#rm row*png
#rm cam*png

#if [ -f broadband.fits ]
#  then
#    cd $OUTPUT_DIR
#    rm mcrx-0.*fits
    
#    cd ..
#    mkdir sync
#    cd sync

    #remove the calzetti mcrx files
    
#    rm input.tar.gz
#    find ../input -size -10M | tar -cf input.tar.gz -T - --exclude '*core*' --exclude '*fits*' --exclude '*tmp*'

#    rm output.tar.gz
#    find ../output -size -10M | tar -cf output.tar.gz -T - --exclude '*core*' --exclude '*fits*' --exclude '*tmp*'

#    for fits in $( ls ../output/*fits )
#    do
#        ln -s $fits .
#    done

    #rm .*mcrx*fits* 
#    rm .* #remove any files starting with .mcrx, which we occasionally see
#    rm sfrhist.fits #don't care to keep this

#    ln ../output/log .
#    ln ../output/log-error .
#    ln ../output/data-fits_headers .
#    ln ../output/images.tar.gz .
#    ln ../output/rgb.tar.gz .
#    ln ../output/composite.png .
#    ln ../output/compositeb.png .
    
#    cd $OUTPUT_DIR
#fi

