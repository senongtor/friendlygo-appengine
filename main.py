import webapp2
from PIL import Image, ImageOps, ImageDraw
from StringIO import StringIO
import datetime
import os
import urllib
import math

class MainPage(webapp2.RequestHandler):
    def get(self):
        state=self.request.get('state')
        if not state: state = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        state = state.lower()
        dim = int(math.sqrt(len(state)))
        if len(state) != dim * dim:
            raise Exception('len(state) is not a square root')
        if dim != 9 and dim != 13 and dim != 19:
            raise Exception('dim is not 9, 13, or 19')

        # dev_appserver.py .
        # http://localhost:8080/?winner=0&fbId0=10153589934097337&fbId1=10153693068502449&state=wbbxxxxxxxwbbwbbxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        # http://localhost:8080/fbId0=10153589934097337
        # appcfg.py update .

        # Facebook recommends 1200 x 630 pixels for the og:image dimensions,
        # but I chose 952x500 (always keep this aspect-ratio! That ratio is assumed in the platform when showing the game-over "printscreen" for FB sharing.)
        img_w = 952
        img_h = 500
        # Board is 400x400, at center of img.
        board_w = 400
        board_h = 400
        board_x = (img_w - board_w)/2
        board_y = (img_h - board_h)/2
        cell_w = board_w/dim # dim=8: 50x50
        cell_h = board_h/dim
        avatar_w = cell_w * 4 / 5 # dim=8: 40x40
        avatar_h = cell_h * 4 / 5
        avatar_x = (cell_w - avatar_w) / 2
        avatar_y = (cell_h - avatar_h) / 2
        antialias_scale = 4 # Draw stuff 4-times bigger, and then scale down with ANTIALIAS to avoid rough circles.

        def loadImg(URL):
            file = StringIO(urllib.urlopen(URL).read())
            return Image.open(file)

        def getFbUrl(fbId, width, height):
            # http://graph.facebook.com/10153589934097337/picture?height=200&width=400
            # http://graph.facebook.com/10153693068502449/picture?height=200&width=400
            return "http://graph.facebook.com/" + fbId + "/picture?height=" + str(height) + "&width=" + str(width);

        def loadFbBigImg(fbId, width, height):
            if not fbId: return None
            big_img = loadImg(getFbUrl(fbId, width, height))
            return big_img.resize((width, height), Image.ANTIALIAS)

        def loadFbSmallImg(fbId):
            if not fbId: return None
            avatar = loadImg(getFbUrl(fbId, cell_w, cell_h))
            return avatar.resize((avatar_w, avatar_h), Image.ANTIALIAS)

        def createCircle(color):
            size = (200, 200)
            img = Image.new('L', size, 0)
            draw = ImageDraw.Draw(img)
            start = 15
            end = 30
            draw.ellipse((start, start) + (200-start, 200-start), fill=color)
            draw.ellipse((end, end) + (200-end, 200-end), fill=0)
            return img.resize((cell_w, cell_h), Image.ANTIALIAS)

        winner=self.request.get('winner')
        # 0 is first player (black), 1 is second (white)
        fbIds=[self.request.get('fbId0'),self.request.get('fbId1')]
        fbSmallImgs=map(loadFbSmallImg, fbIds)
        fbBigImgs = [None, None]
        if fbIds[0] and fbIds[1]:
            for i in range(2):
                fbBigImgs[i] = loadFbBigImg(fbIds[i], img_w/2, img_h)
        elif fbIds[0] or fbIds[1]:
            for i in range(2):
                fbBigImgs[i] = loadFbBigImg(fbIds[i], img_w, img_h)

        black_stone = fbSmallImgs[0] if fbIds[0] else Image.open(os.path.join(os.path.dirname(__file__), 'images/black.png')).resize((avatar_w, avatar_h), Image.ANTIALIAS)
        white_stone = fbSmallImgs[1] if fbIds[1] else Image.open(os.path.join(os.path.dirname(__file__), 'images/white.png')).resize((avatar_w, avatar_h), Image.ANTIALIAS)
        board_img = Image.open(os.path.join(os.path.dirname(__file__), 'images/empty' + str(dim) + 'x' + str(dim) + '.png'))
        
        # http://stackoverflow.com/questions/890051/how-do-i-generate-circular-thumbnails-with-pil
        size = (avatar_w * antialias_scale, avatar_h * antialias_scale)
        mask = Image.new('L', size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((antialias_scale, antialias_scale) + ((avatar_w-1) * antialias_scale, (avatar_h-1) * antialias_scale), fill=255)
        mask = mask.resize((avatar_w, avatar_h), Image.ANTIALIAS)

        circle_mask = createCircle(255)
        white_circle = circle_mask
        black_circle = createCircle(1)

        composite_img = Image.new('RGB', (img_w,img_h), (255,255,255))
        if fbIds[0] and fbIds[1]:
            composite_img.paste(fbBigImgs[0],(0,0))
            composite_img.paste(fbBigImgs[1],(img_w/2,0))
        elif fbIds[0] or fbIds[1]:
            if fbIds[0]: composite_img.paste(fbBigImgs[0],(0,0))
            if fbIds[1]: composite_img.paste(fbBigImgs[1],(0,0))

        board_img_mask = None
        if fbIds[0] or fbIds[1]: board_img_mask = Image.new('L', (board_w, board_h), 204) # alpha is 204/255=0.8
        composite_img.paste(board_img, (board_x, board_y), board_img_mask)

        i = 0
        for row in range(dim):
            for col in range(dim):
                color_piece = state[i]
                i = i+1
                if color_piece != 'x':
                    img = white_stone if color_piece == 'w' else black_stone
                    circle = white_circle if color_piece == "w" else black_circle
                    x = board_x + col*cell_w
                    y = board_y + row*cell_h
                    composite_img.paste(img, (x+avatar_x,y+avatar_y), mask)
                    if fbIds[0 if color_piece=="b" else 1]:
                        composite_img.paste(circle, (x,y), circle_mask)

        buf= StringIO()
        composite_img.save(buf, format= 'JPEG', quality=80) # default quality is 75, never go above 95
        png= buf.getvalue()

        self.response.headers['Content-Type'] = 'image/jpg'
        # Set forever cache headers (I copied what github.io returns); one year in the future.
        self.response.headers['Cache-Control'] = 'public,max-age=31556926'
        #self.response.headers['Age'] = '0'
        #self.response.headers["Last-Modified"] = 'Thu, 09 Jun 2016 13:41:32 GMT'
        # https://www.pythonanywhere.com/forums/topic/694/
        # If both Expires and max-age are set, max-age will take precedence. BUT: It is recommended that Expires should be set to a similar value.
        # 364 days in the future
        expiry_time = datetime.datetime.utcnow() + datetime.timedelta(364)
        self.response.headers["Expires"] = expiry_time.strftime("%a, %d %b %Y %H:%M:%S GMT")

        self.response.out.write(png)

app = webapp2.WSGIApplication([(r'/.*', MainPage),])
