Drop your intro / logo video here as:

    INTRO_VIDEO.mp4

Then open content/curriculum.py and paste the PUBLIC video link into the
INTRO_VIDEO_URL constant (WhatsApp can only send media from a public URL,
so an mp4 hosted on Vercel Blob, Cloudinary, or any CDN works best).

If you deploy with Vercel, you can also serve this file under /static by
adjusting vercel.json - but a public hosted link is the simplest fix.