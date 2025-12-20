import iconsbase64
from tkinter import *
import tkinter as tk
import pygame, threading
from PIL import ImageTk
import base64, os
import audio_metadata, time
from mutagen.mp3 import MP3
from PIL import Image as SM
from PIL import ImageFilter
from eyed3 import id3 as eye
from tkinter import messagebox
from tkinter import filedialog, ttk
import random

class WINDOW:
    def __init__(self):
        # icons, images path
        self.MAIN = "assets/IconLogo.png"
        self.LOGO = "assets/logo.png"
        self.PAUSE = "assets/pause.png"
        self.PLAY = "assets/play.png"
        self.DEVOL = "assets/muted.png"
        self.INVOL = "assets/notmuted.png"
        self.FOREWARD = "assets/next.png"
        self.BACK = "assets/prev.png"
        self.MUSIC = "assets/music.png"
        self.FOLDER = "assets/folder.png"
        self.SHUFFLE = "assets/shuffle.png"
        self.SHUFFLEON = "assets/shuffleon.png"
        self.REPEAT = "assets/repeat.png"
        self.REPEATON = "assets/repeaton.png"
        self.LEFT_FRAME = "assets/left_bar.png"
        self.RIGHT_FRAME = "assets/right_bar.png"
        self.NOImg = iconsbase64.NOImage
        
        # colors
        self.textColor = 'white'
        self.FrameThemecolor = '#131313'
        self.FrameThemetxtcolor = 'white'
        
        # default window geometry
        self.height=620 
        self.width=1060
        
        # window initiation
        self.windows = tk.Tk()
        self.windows.title('Wave - Music Player')
        self.screen_width = self.windows.winfo_screenwidth()
        self.screen_height = self.windows.winfo_screenheight()
        self.windows.bind('<space>', self.play_space)

        # window geometry set, based on user screen
        self.x = int((self.screen_width/2) - (self.width/2))
        self.y = int((self.screen_height/2) - (self.height/2))
        self.windows.geometry("{}x{}+{}+{}".format(self.width, self.height, self.x, self.y))
        self.windows.config(bg='#1e1e1e')
        
        self.background = Label(self.windows, borderwidth=0)
        self.background.place(x=0,y=0)

        self.root=Frame(self.windows, height=self.height, width=self.width, bg="#131313")
        self.root.pack()
        

        
        self.windows.protocol("WM_DELETE_WINDOW", self.keluar_aplikasi)
        
        
        
    def window(self):   
        self.wintype = self.windows.state()
        if self.wintype == 'zoomed':
            temp = self.screen_height // 100
            temp = temp * 100
            var = temp - 620
            padding = var // 2
            self.root.pack(pady=padding)
            
        elif self.wintype == 'normal':
            self.root.config(highlightthickness=0)
            self.root.pack(pady=0)
        self.root.after(100, self.window)
    
    def geticons(self, icons):
        base64_img_bytes = icons.encode('utf-8')
        decoded_image_data = base64.decodebytes(base64_img_bytes)
        ico = PhotoImage(data=decoded_image_data)
        return ico
    
    def getimages(self, images_path):
        image_obj = PhotoImage(file=images_path)
        return image_obj

    def keluar_aplikasi(self):
        # Munculkan pesan dialog untuk validasi keluar aplikasi
        result = messagebox.askyesno(title="Exit", message="Apakah Anda yakin ingin keluar?")

        # Jika pengguna memilih "OK", keluar aplikasi
        if result:
            self.windows.destroy()
            
class MusicPlayer(WINDOW):
    
    def __init__(self):
        super().__init__()

        # threading initiation
        self.mainWindowThread = threading.Thread(target=self.window)
        self.mainWindowThread.start()
        
        #Global Variables Declaration
        global songsdir,songname,filefound, musiclist
        songsdir,songname,filefound, musiclist = "","","", ""
        global pausedornot, Mute, song_len, checksong, slide, pas, tl, Stop
        checksong,slide,tl = "","",""
        song_len = ""
        pas = False
        Mute = True
        pausedornot = False
        Stop = False
        
        pygame.mixer.init()
        
        #APPLICATION MAIN ICON
        self.mainico = self.getimages(self.MAIN)
        self.windows.iconphoto(False, self.mainico)


        #RIGHT FRAME
        self.rightFrame = Frame(self.root,height=600, width=620, bg=self.FrameThemecolor)
        self.rightFrame.place(x=250, y=20)

        #RIGHTCONTENT FRAME, NOW PLAYING SONG 
        self.imageee = self.getimages(self.RIGHT_FRAME)
        self.rightCONTENTFrame = Frame(self.root, height=620, width=250,bg=self.FrameThemecolor)
        self.rightCONTENTFrame.place(x=810, y=0)
        self.sha = Label(self.rightCONTENTFrame, height=620, width=250, image=self.imageee, borderwidth=0)
        self.sha.place(x=0,y=0)

        
        self.nowplay = Frame(self.rightCONTENTFrame, height=30, width=200,bg='#464545')
        self.nowplay.place(x=23, y=20)
        self.nowplaylbl = Label(self.nowplay, text='',fg='white', bg='#464545',font=('CreatoDisplay-Bold', 13))
        self.nowplaylbl.place(x=25,y=0)
        self.nowplaypic = Frame(self.rightCONTENTFrame, height=200, width=200, bg='#1e1e1e')
        self.nowplaypic.place(x=23,y=50)

        self.detailsframe = Frame(self.rightCONTENTFrame, height=70, width=225, bg=self.FrameThemecolor)
        self.detailsframe.place(x=23, y=245)
        
        self.song_info = Label(self.detailsframe, text="Unknown Song", bg=self.FrameThemecolor, fg=self.FrameThemetxtcolor)
        self.song_info.config(font=('CreatoDisplay-Bold', 11))
        self.song_info.place(x=0, y=15)
    
        self.song_info1 = Label(self.detailsframe, text="Unknown Artist", bg=self.FrameThemecolor, fg=self.FrameThemetxtcolor)
        self.song_info1.place(x=0, y=35)

        #MUSIC LIST DISPLAY BOX
        self.musicboxFRAME = Frame(self.root,height=500, width=560)
        self.musicboxFRAME.place(x=250,y=20)
        musiclist = Listbox(self.musicboxFRAME, height=27, width=89, border=0  ,bg="#1e1e1e", fg=self.textColor)
        musiclist.pack(side='left', fill='y')
        self.scroll = ttk.Scrollbar(self.musicboxFRAME, orient='vertical')
        self.scroll.pack(side='right', fill='y')

        #LEFT FRAME-----------------------------------------------------------------------------------
        self.leftFrame = Frame(self.root, height=620, width=250, bg=self.FrameThemecolor)#bg='#eeeeee'
        self.leftFrame.place(x=0,y=0)
        self.lftImg = self.getimages(self.LEFT_FRAME)
        self.lftframe = Label(self.leftFrame, height=700, width=250, image=self.lftImg, borderwidth=0)
        self.lftframe.place(x=0, y=0)
        
        #HEADING (PLAYER NAME)
        self.head = Frame(self.leftFrame, height=50, width=173,bg=self.FrameThemecolor)
        self.head.place(x=35,y=15)
        self.pic = self.getimages(self.LOGO)
        self.headlbl = Label(self.head, image=self.pic, bg=self.FrameThemecolor) #font=('CoolveticaRg-Regular', 25) text='MusicByte',
        self.headlbl.place(x=0, y=5)

        #MANAGEMENT i.e ADD SONGS AND ETC OPTIONS
        self.addlibrary = Frame(self.leftFrame, height=280, width=210, bg=self.FrameThemecolor)
        self.addlibrary.place(x=10, y=70)

        self.text2 = Label(self.addlibrary, text="Folder",font=('CreatoDisplay-BOLD', 13), fg=self.textColor,bg=self.FrameThemecolor) #SUBHEADINGS
        self.text2.place(x=55,y=40)
        self.folderico = self.getimages(self.FOLDER)
        self.folderlabel = Label(self.addlibrary, image=self.folderico, bg=self.FrameThemecolor)
        self.folderlabel.place(x=28,y=43)
        self.btn = Button(self.addlibrary, activebackground=self.FrameThemecolor, text="Tambahkan Folder",font=('CreatoDisplay-REGULAR', 12), borderwidth=0, fg=self.textColor,bg=self.FrameThemecolor, command=self.addlibFolder) #ADD FOLDER TO LIBRARY
        self.btn.place(x=55,y=70)
        self.btn3 = Button(self.addlibrary, activebackground=self.FrameThemecolor, text="Hapus Folder",font=('CreatoDisplay-REGULAR', 12), borderwidth=0, fg=self.textColor,bg=self.FrameThemecolor, command=lambda: self.removeSongs('ALL')) #Removes all songs from LIBRARY
        self.btn3.place(x=55,y=95) #145
        self.textmus = Label(self.addlibrary, text="Musik",font=('CreatoDisplay-BOLD', 13), fg=self.textColor,bg=self.FrameThemecolor) #SUBHEADINGS
        self.textmus.place(x=55,y=135)
        self.musicico = self.getimages(self.MUSIC)
        self.musiclabel = Label(self.addlibrary, image=self.musicico, bg=self.FrameThemecolor)
        self.musiclabel.place(x=28,y=138)
        self.btn1 = Button(self.addlibrary, activebackground=self.FrameThemecolor, text="Tambahkan Musik",font=('CreatoDisplay-REGULAR', 12), borderwidth=0, fg=self.textColor,bg=self.FrameThemecolor, command=self.addSongs) #ADD SONGS TO LIBRARY
        self.btn1.place(x=55,y=165)
        self.btn2 = Button(self.addlibrary, activebackground=self.FrameThemecolor, text="Hapus Musik",font=('CreatoDisplay-REGULAR', 12), borderwidth=0, fg=self.textColor,bg=self.FrameThemecolor, command=lambda: self.removeSongs('ONE')) #Removes current song from LIBRARY
        self.btn2.place(x=55,y=190)

        #FRAME BAWAH
        self.framebawah = Frame(self.root, height=180, width=560, bg=self.FrameThemecolor)
        self.framebawah.place(x=250, y=488)

        #CONTROL FRAME (MAIN)-------------------------------------------------------------------------
        self.controlFRAME = Frame(self.framebawah,height=100, width=560, background=self.FrameThemecolor)
        self.controlFRAME.place(x=0, y=25)

        #Time FUNCTION
        self.sliderlength = Frame(self.controlFRAME, height=21, width=35, bg=self.FrameThemecolor)
        self.sliderlength.place(x=500, y=5)
        self.sliderlengthlbl = Label(self.sliderlength, text='00:00', bg=self.FrameThemecolor, fg=self.FrameThemetxtcolor)
        self.sliderlengthlbl.place(x=0,y=0)
        self.timeframe = Frame(self.controlFRAME, height=21, width=40)
        self.timeframe.place(x=20, y=7)
        self.progressBar = Label(self.timeframe, text="00:00", relief=GROOVE, anchor=E, borderwidth=0, bg=self.FrameThemecolor, fg=self.FrameThemetxtcolor)
        self.progressBar.pack(fill=X, side=BOTTOM)


        #SLIDER FRAME
        self.sliderFrame = Frame(self.controlFRAME, height=21, width=350, bg=self.FrameThemecolor)
        self.sliderFrame.place(x=58, y=4)
        self.sliderstyle = ttk.Style()
        self.sliderstyle.configure("TScale", background=self.FrameThemecolor)
        self.progressBar1 = ttk.Scale(self.sliderFrame, from_=0, to=100, orient=HORIZONTAL, value=0,length=432, command=self.slider)
        self.progressBar1.pack()


        #CONTROLS
        self.controlFrame1 = Frame(self.controlFRAME, height=48, width=140, bg=self.FrameThemecolor)
        self.controlFrame1.place(x=200,y=33)

        self.icon1 = self.getimages(self.PLAY)
        global playBTN
        playBTN = Button(self.controlFrame1, activebackground=self.FrameThemecolor, image=self.icon1, borderwidth=0, bg=self.FrameThemecolor, command=lambda: self.play(pausedornot))
        self.icon3 = self.getimages(self.FOREWARD)
        self.forewardBTN = Button(self.controlFrame1, activebackground=self.FrameThemecolor, image=self.icon3, borderwidth=0, bg=self.FrameThemecolor, command=self.foreward)
        self.icon4 = self.getimages(self.BACK)
        self.backBTN = Button(self.controlFrame1, activebackground=self.FrameThemecolor, image=self.icon4, borderwidth=0, bg=self.FrameThemecolor, command=self.previous)
        self.icon5 = self.getimages(self.DEVOL)

        self.backBTN.place(x=0,y=5)
        playBTN.place(x=45,y=0)
        self.forewardBTN.place(x=104,y=5)

        
        #SHUFFLE AND REPEAT
        self.shufflerepeat = Frame(self.controlFRAME, height=30, width=30, bg=self.FrameThemecolor)
        self.shufflerepeat.place(x=20, y=48)
        
        global shuffleBTN, repeatBTN, shuffled, repeated
        shuffled = False
        repeated = False
        self.shuffleBTNimg = self.getimages(self.SHUFFLE)
        self.repeatBTNimg= self.getimages(self.REPEAT)
        
        shuffleBTN = Button(self.shufflerepeat, image=self.shuffleBTNimg, borderwidth=0, command=self.shuffle, bg=self.FrameThemecolor, activebackground=self.FrameThemecolor)
        shuffleBTN.grid(column=0, row=0)
        repeatBTN= Button(self.shufflerepeat, image=self.repeatBTNimg, borderwidth=0, command=self.repeat, bg=self.FrameThemecolor, activebackground=self.FrameThemecolor)
        repeatBTN.grid(column=1, row=0, padx=10)


        #VOLUME SLIDER
        self.volsliderFrame = Frame(self.controlFRAME, height=21, width=300, bg=self.FrameThemecolor)
        self.volsliderFrame.place(x=415, y=43)
        self.imginvol = self.getimages(self.INVOL)
        self.imgdevol = self.getimages(self.DEVOL)
        self.devol = Label(self.volsliderFrame, image=self.imgdevol, borderwidth=0, bg=self.FrameThemecolor, activebackground=self.FrameThemecolor)
        self.devol.grid(column=0, row=0)
        self.volumeSlider = ttk.Scale(self.volsliderFrame, from_=0, to=1, orient=HORIZONTAL, value=0.75,length=75, command=self.volume)
        self.volumeSlider.grid(column=1, row=0, padx=5)
        self.invol = Label(self.volsliderFrame, image=self.imginvol, borderwidth=0, bg=self.FrameThemecolor, activebackground=self.FrameThemecolor)
        self.invol.grid(column=2, row=0, padx=5)
        
        
    def updatetitle(self, title):
        global tl
        tl = title
        title = title.replace('       ', '')
        global filefound
        if filefound != True:
            title = f'Wave - Add songs to playlist first! ' + title
            self.root.title(title)
            self.root.update()
            return
        title = f'Wave - Playing:   ' + title
        self.windows.title(title)
        self.windows.update()
    
    
    def getsongINFO(self):
        global pas, slide, Stop, songsdir
        if Stop:
            return
        activeClick = musiclist.get(ACTIVE)
        activeClick = activeClick.replace('       ', '')
        self.song = os.path.join(songsdir, activeClick)
        try:
            song_load = MP3(slide)
        except:
            return
        global song_len
        song_len = song_load.info.length
        def gettime():
            global song_len, pausedornot
            currentTIME = pygame.mixer.music.get_pos() / 1000
            ctyme = time.strftime('%M:%S', time.gmtime(currentTIME))
            styme = time.strftime('%M:%S', time.gmtime(song_len))
            #currentTIME+=1
            if int(self.progressBar1.get() == int(song_len)):
                self.progressBar.config(text=styme)
                self.foreward()
            elif pausedornot:
                pass
            elif int(self.progressBar1.get()) == int(currentTIME):
                #no movement to the slider
                self.sliderPOS = int(song_len)
                self.progressBar1.config(to=self.sliderPOS, value=int(currentTIME))
            else:
                #slider moved
                self.sliderPOS = int(song_len)
                self.progressBar1.config(to=self.sliderPOS, value=int(self.progressBar1.get()))
                ctyme = time.strftime('%M:%S', time.gmtime(int(self.progressBar1.get())))
                self.sliderlengthlbl.config(text=styme)
                self.progressBar.config(text=ctyme)
                nextt = int(self.progressBar1.get()) + 1
                self.progressBar1.config(value=nextt)

            self.progressBar.after(1000, gettime)
        if pas == False:
            gettime()
            pas = True
        else:
            pass
            


    def nextinfo(self, info):
        if info == None:
            pass

        else:
            try:
                song_load = MP3(info)
            except:
                info = info.replace("\\", "/")
            song_load = MP3(info)
            song_len1 = song_load.info.length
            styme1 = time.strftime('%M:%S', time.gmtime(song_len1))
            tagg = eye.Tag()
            tagg.parse(info)
            artist = tagg.artist
            if artist == None:
                pass

            else:
                pass


            # bitrate = song_load.info.bitrate / 1000


    
    def slider(self, x):
        global slide
        '''activeClick = musiclist.get(ACTIVE)
        activeClick = activeClick.replace('       ','')
        song = os.path.join(songsdir, activeClick)'''
        try:
            pygame.mixer.music.load(slide)
            pygame.mixer.music.play(loops=0, start=int(self.progressBar1.get()))
        except:
            pass
        #sliderLBL.config(text=f'{int(progressBar1.get())} 
    
    def volume(self, percent):
        pygame.mixer.music.set_volume(self.volumeSlider.get())
        # vol = pygame.mixer.music.get_volume() * 100
        # self.vLabelpercent.config(text=f'{int(vol)}%')
        
    def mute(self,muteornot):
        global muteBTN, Mute
        if muteornot:
            pygame.mixer.music.set_volume(0)
            # self.vLabelpercent.config(text='Muted')
            icon5 = self.getimages(self.DEVOL)
            muteBTN.config(image=icon5)
            muteBTN.img = icon5
            Mute = False
        else:
            pygame.mixer.music.set_volume(self.volumeSlider.get())
            vol = pygame.mixer.music.get_volume() * 100
            # self.vLabelpercent.config(text=f'{int(vol)}%')
            icon6 = self.getimages(self.INVOL)
            muteBTN.config(image=icon6)
            muteBTN.img = icon6
            Mute = True
    
    def getmetadata(self, filee):
        global filefound
        tag = eye.Tag()
        try:
            tag.parse(filee)
            artist = tag.artist
            title = tag.title
            if artist == None:
                self.song_info1.config(text='Unknown Artist')
            else:
                self.song_info1.config(text=artist)
            if title == None:
                self.song_info.config(text='Unknown Title', font=('CreatoDisplay-Bold', 11))
            else:
                self.song_info.config(text=title, font=('CreatoDisplay-Bold', 11))
            filefound = True
        except:
            pass
        try:
            load = MP3(filee)
            songbit = load.info.bitrate // 1000
            self.songbitrate.config(text=f'Bitrate: {songbit}kbps')
        except:
            return
        
    def getalbumArt(self, art, nextart):
        global filefound
        self.getmetadata(art)
        if filefound !=True:
            return
        image = 'Artwork-now.jpg'
        image2 = 'Artwork-next.jpg'
        backgroundIMG = 'bg.png'

        currentdir = os.getcwd()
        Folder = 'mp3playerCache'
        workinfFolder = os.path.join(currentdir, Folder)

        if not os.path.exists(workinfFolder):
            os.makedirs(workinfFolder)
        path = os.path.join(workinfFolder, image)

        path2 = os.path.join(workinfFolder, image2)
        BGPath = os.path.join(workinfFolder, backgroundIMG)
        # For Current Album Art
        try:
            metadata=audio_metadata.load(art)
            artwork = metadata.pictures[0].data
            with open(path, 'wb') as f:
                f.write(artwork)
            width = 200
            height = 200
            imggg = SM.open(path)
            try:
                left = 6
                top = self.screen_height / 2
                right = 900
                bottom = 2 * self.screen_height / 2
                im1 = imggg.crop((left, top, right, bottom)) 
                im2 = im1.resize((self.screen_width,self.screen_height), SM.LANCZOS)
                im2 = im2.filter(ImageFilter.GaussianBlur(radius=15)) 
                im2.save(BGPath)
                im2 = self.getimages(BGPath)
                self.background.config(image=im2)
                self.background.img = im2
            except:
                pass
            imggg = imggg.resize((width,height), SM.LANCZOS)
            photoImg =  ImageTk.self.getimages()
            for things in self.nowplaypic.winfo_children():
                things.destroy()
            self.nowplayingLabel = Label(self.nowplaypic, height=200, width=200, image=photoImg, borderwidth=0)
            self.nowplayingLabel.img = photoImg
            self.nowplayingLabel.place(x=0,y=0)
        except:
            # pass
            for things in self.nowplaypic.winfo_children():
                things.destroy()
            imgg = self.geticons(self.NOImg)
            self.nowplayingLabel = Label(self.nowplaypic, height=200, width=200, image=imgg, borderwidth=0)
            self.nowplayingLabel.img = imgg
            self.nowplayingLabel.place(x=0,y=0)
        
   
    def addlibFolder(self):
        global songsdir, musiclist, filefound
        songsdir = filedialog.askdirectory()
        try:
            songs = os.listdir(songsdir)
            # Filter hanya file dengan ekstensi ".mp3"
            mp3_files = [song for song in songs if song.endswith('.mp3')]
            filefound = True
        except FileNotFoundError:
            filefound = False
            return
        # iconnn = self.getimages(self.PLAY)
        # playBTN.config(image=iconnn)
        # playBTN.img = iconnn

        musiclist.delete('0', 'end')
        musiclist.config(yscrollcommand=self.scroll.set)
        self.scroll.config(command=musiclist.yview)
        
        for song in mp3_files:
            musiclist.config(font=('CreatoDisplay-THIN',10))
            musiclist.insert(END, f'       {song}')
        
        musiclist.config(height=29, width=67)
        

    def addSongs(self):
        global songsdir, filefound, playBTN
        
        songFilename = filedialog.askopenfilenames(initialdir="/", title="Select File",
                                            filetypes=(("mp3 files", "*.mp3"),("all files", "*.*")))  
        if songFilename == "":
            filefound = False
            return
        else:
            filefound = True 
        # iconnn = self.getimages(self.PLAY)
        # playBTN.config(image=iconnn)
        # playBTN.img = iconnn                                 
        # musiclist.delete('0', 'end')                                     
        # musiclist.insert(ANCHOR, " \n ")                                      
        for song in songFilename:                                 
            songname = os.path.basename(song)
            musiclist.config(font=('CreatoDisplay-THIN',10))
            musiclist.insert(END, f'       {songname}')
        # musiclist.config(height=29, width=67)
        musiclist.config(height=29, width=67)
        try:
            path = songFilename[0]
        except IndexError:
            return
        songname = os.path.basename(path)
        path = path.replace(songname, "")
        songsdir = path.replace("\\", "/")
        
        
        
    
    def play(self, check):
        global Stop, checksong, tl, slide, repeated, shuffled
        global pausedornot, playBTN
        try:
            Stop = False
            activeClick = musiclist.get(ACTIVE)
            self.updatetitle(activeClick)
            song = os.path.join(songsdir, activeClick)
            song = song.replace('\\', '/')
            song = song.replace('       ', '')
            ran = random.randint(-2, 2)
            upnext = musiclist.curselection()
            if repeated or shuffled:
                if repeated:
                    upnext=upnext[0]
                if shuffled:
                    upnext=upnext[0]+ran
            else:
                upnext = upnext[0]+1
            # upnext = upnext[0]+1
            song2 = musiclist.get(upnext)
            filetype = song2[-3:]
            filetype = filetype.lower()
            if filetype == "mp3" or filetype == "wav" or filetype == "m4a" or filetype == "aac":
                path2 = os.path.join(songsdir, song2)
                path2 = path2.replace('\\', '/')
                path2 = path2.replace('       ', '')
            else:
                path2 = None

            self.nextinfo(path2)
            if song != checksong:
                try:
                    pygame.mixer.music.load(song)
                    pygame.mixer.music.play(loops=0)
                    slide = song
                    icon2 = self.getimages(self.PAUSE)
                    playBTN.config(image=icon2)
                    playBTN.img = icon2
                    checksong = song
                    pausedornot = False
                    #Reset Progress Slider
                    self.progressBar1.config(value=0)
                    self.getsongINFO()
                    #sliderPOS = int(song_len)
                    #progressBar1.config(to=sliderPOS, value=0)
                except:
                    pass
            elif checksong == song:
                pausedornot = check
                if pausedornot:
                    tl = tl.replace('       ', '')
                    t = f'Wave - Playing:   ' + tl
                    pygame.mixer.music.unpause()
                    icon2 = self.getimages(self.PAUSE)
                    playBTN.config(image=icon2)
                    playBTN.img = icon2
                    self.windows.title(t)
                    self.windows.update()
                    pausedornot = False
                else:
                    t = 'Wave - Paused'
                    pygame.mixer.music.pause()
                    iconnn = self.getimages(self.PLAY)
                    playBTN.config(image=iconnn)
                    playBTN.img = iconnn
                    self.windows.title(t)
                    self.windows.update()
                    pausedornot = True
            self.getalbumArt(song, path2)
        except:
            False
    
    def play_space(self, event:None):
        self.play(pausedornot)
    
    def foreward(self):
        global playBTN, pausedornot, checksong, slide, repeated, shuffled
        upnext = musiclist.curselection()
        iconnn = self.getimages(self.PAUSE)
        playBTN.config(image=iconnn)
        playBTN.img = iconnn
        # print(ran)
        #Get the next song number (Tuple Number)
        nextsong = musiclist.curselection()
        try:
            if repeated or shuffled:
                if repeated:
                    nextsong = nextsong[0]
                if shuffled:
                    ran = random.randint(-2, 2)
                    # musiclist.selection_set
                    nextsong = nextsong[0]+ran
                    # print("bisa")
            else:
                nextsong = nextsong[0]+1
            # nextsong = nextsong[0]+1
        except:
            return
        upnext = upnext[0]+2
        song2 = musiclist.get(upnext)
        filetype = song2[-3:]
        filetype = filetype.lower()
        if filetype == "mp3": #or filetype == "wav" or filetype == "m4a" or filetype == "aac":
            path2 = os.path.join(songsdir, song2)
            path2 = path2.replace('\\', '/')
            path2 = path2.replace('       ', '')
        else:
            path2 = None

        song = musiclist.get(nextsong)
        if song == "" or song == None:
            return
        #Reset Progress Slider
        self.progressBar1.config(value=0)

        path = os.path.join(songsdir, song)
        path = path.replace('\\', '/')
        path = path.replace('       ', '')
        slide = path
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(loops=0)
            slide = path
            pausedornot = False
            checksong = path
            self.getsongINFO()
        except:
            pass
        try:
            musiclist.selection_clear(0, END)
            musiclist.activate(nextsong)
            musiclist.selection_set(nextsong, last=None)
            self.updatetitle(musiclist.get(ACTIVE))
        except:
            pass
        self.nextinfo(path2)
        self.getalbumArt(path, path2)
    
    def previous(self):
        global playBTN, pausedornot, checksong, slide
        iconnn = self.getimages(self.PAUSE)
        playBTN.config(image=iconnn)
        playBTN.img = iconnn
        upnext = musiclist.curselection()

        previoussong = musiclist.curselection()
        previoussong = previoussong[0]-1
        song = musiclist.get(previoussong)

        upnext = upnext[0]
        song2 = musiclist.get(upnext)

        if previoussong <=0:
            return

        try:
            path2 = os.path.join(songsdir, song2)
            path2 = path2.replace('\\', '/')
            path2 = path2.replace('       ', '')
        except:
            path2 = None

        self.nextinfo(path2)
        path = os.path.join(songsdir, song)
        path = path.replace('\\', '/')
        path = path.replace('       ', '')


        try:
            #Reset Progress Slider
            self.progressBar1.config(value=0)

            pygame.mixer.music.load(path)
            pygame.mixer.music.play(loops=0)
            pausedornot = False
            checksong = path
            slide = path
            self.getsongINFO()
        except:
            pass

        try:
            musiclist.selection_clear(0, END)
            musiclist.activate(previoussong)
            musiclist.selection_set(previoussong, last=None)
            self.updatetitle(musiclist.get(ACTIVE))
        except:
            pass
        self.getalbumArt(path, path2)
    
    def removeSongs(self, typee):
        global Stop
        currentsong = musiclist.curselection()
        #nextsong = currentsong[0]+1
        
        if typee == 'ONE':
            try:
                #Reset Progress Slider
                self.progressBar1.config(value=0)
                musiclist.delete(currentsong)
                pygame.mixer.music.stop()

                musiclist.selection_set(currentsong, last=None)
                nextsong = 0
                
                Stop = True
            except:
                pass
        elif typee == 'ALL':
            #Reset Progress Slider
            self.progressBar1.config(value=0)
            musiclist.delete(0, END)
            pygame.mixer.music.stop()
            
            Stop = True
        else:
            pass

    def shuffle(self):
        global shuffleBTN, shuffled, repeated
        if shuffled:
            shuffled = False
            imggg = self.getimages(self.SHUFFLE)
            shuffleBTN.config(image=imggg)
            shuffleBTN.img = imggg
            # repeated = True
            
            # print("01")

        else:
            shuffled = True
            imgg = self.getimages(self.SHUFFLEON)
            shuffleBTN.config(image=imgg)
            shuffleBTN.img = imgg
            # print("00")
            if repeated:
                self.repeat()
    
    def repeat(self):
        global repeatBTN, repeated, shuffled
        if repeated:
            repeated = False
            imggg= self.getimages(self.REPEAT)
            repeatBTN.config(image=imggg)
            repeatBTN.img = imggg
            # print("11")
        else:
            repeated = True
            imgg1 = self.getimages(self.REPEATON)
            repeatBTN.config(image=imgg1)
            repeatBTN.img = imgg1
            # print("10")
            if shuffled:
                self.shuffle()
        
    

        

if __name__ == "__main__":
    musicplay=MusicPlayer()
    musicplay.windows.mainloop()
