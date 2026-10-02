"""Encode a silent walkthrough from actual captured UI screenshots (no synthetic UI)."""
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont
import imageio_ffmpeg
import subprocess

root=Path(__file__).resolve().parents[1]
images=sorted((root/'docs/screenshots').glob('0*.png'))
if not images:raise SystemExit('Capture the actual dashboard screenshots first')
frames=[]
labels=['Community outcomes · simulated data','Paired baseline evidence · inspect tradeoffs','Extended outage · finite shared energy',
        'Actuator authority · failure and recovery','Affordability · assumed INR budgets']
font=ImageFont.load_default(size=25)
for i,path in enumerate(images):
    img=Image.open(path).convert('RGB')
    # Pan through the genuine full-page capture so content stays readable.
    resized=img.resize((1200,round(img.height*1200/img.width)))
    for phase in range(4):
        frame=Image.new('RGB',(1280,800),'#f4f6f2')
        top=round(max(0,resized.height-670)*phase/3)
        crop=resized.crop((0,top,1200,min(resized.height,top+670)))
        frame.paste(crop,(40,80))
        draw=ImageDraw.Draw(frame)
        draw.text((40,20),labels[min(i,len(labels)-1)],font=font,fill='#127454')
        draw.text((40,760),'Recorded UI walkthrough · synthetic simulation · no hardware trial',font=ImageFont.load_default(size=17),fill='#607269')
        frames.append(frame)
frames[0].save(root/'docs/demo-recording.gif',save_all=True,append_images=frames[1:],duration=1500,loop=0)
process=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s','1280x800','-r','2','-i','-',
                          '-an','-vcodec','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(root/'docs/demo-recording.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
for frame in frames:
    for _ in range(3):process.stdin.write(frame.tobytes())
process.stdin.close()
error=process.stderr.read().decode()
if process.wait():raise SystemExit(error)
print(f'Encoded {len(frames)*1.5:.0f}s walkthrough from {len(images)} actual UI captures')
