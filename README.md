

# Stremio addon written in python. Streams movies & tv shows from piratebay's api. 
 Possibly the only streaming addon (for movies & shows) you need. 

 ## The config
 
 * runs on localhost.
 * on port 7050.
 * only HD streams returned (720p & above).
 * sorted results by seeders (decending) so theoretically the best stream will always be first.


## Install 

 **1. Install dependencies** 

    pip install -r requirements.txt



 **2. Run the server**

    python3 start.py


 
 **3. install addon in stremio**
    
   stremioUI - addons -- 'Add addons' button:
    
     http://127.0.0.1:7050/manifest.json

   This will get it running and installed but on localhost. So it only works on that device.

   If you want it accessible on other devices (like a TV,phone,projector), easist option is cloudflare tunnel.



## Hosting Locally with Cloudflare Tunnel

1. **Download `cloudflared`** for your operating system. (linux example)

       wget https://github.com/cloudflare/cloudflared/releases/2026.5.0/cloudflared-linux-amd64.deb

      (check their respository for different os packages & updates)
   

2. **Install the package** 

       sudo dpkg -i cloudflared-linux-amd64.deb   


3. **Run the tunnel**  

       cloudflared tunnel --url http://127.0.0.1:7050


4. **Copy the URL**

      it will be ending in 'trycloudflare.com'   


5. **install in stremio**
      stremioUI - addons -- Add addons button :

      {your cloudflare url}/manifest.json
 
      Now you can install it and use it on any device.

      No more localhost restrictions. 


### Disclaimer

This tool is for educational purposes only. The author is not responsible for the misuse of this software. 
Please ensure you comply with copyright laws and regulations in your jurisdiction.
