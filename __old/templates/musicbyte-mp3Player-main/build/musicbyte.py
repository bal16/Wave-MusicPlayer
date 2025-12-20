'''
    MusicByte Music Player
    Designed and developed by Shawan Mandal
    MIT License, see LICENSE for more details.
    Copyright (c) 2021 Shawan Mandal
'''


import smtplib
import platform
import iconsbase64
from tkinter import *
import tkinter as tk
import pygame, threading
from PIL import ImageTk
import base64, os, socket
import audio_metadata, time
from mutagen.mp3 import MP3
from PIL import Image as SM
from PIL import ImageFilter
from eyed3 import id3 as eye
from tkinter import messagebox
from tkinter import filedialog, ttk

height=620 
width=1060
MAIN = iconsbase64.ICO_MAIN
MUSICBYTE = iconsbase64.ICO_MUSICBYTE
PAUSE = iconsbase64.ICO_PAUSE
PLAY = iconsbase64.ICO_PLAY
MUTE = iconsbase64.ICO_MUTE
UNMUTE = iconsbase64.ICO_UNMUTE
FOREWARD = iconsbase64.ICO_FOREWARD
BACK = iconsbase64.ICO_BACKWARD
MUSIC = iconsbase64.ICO_MUSIC
NOImg = iconsbase64.NOImage
LEFT_FRAME = iconsbase64.FRAME_LEFT
RIGHT_FRAME = iconsbase64.FRAME_RIGHT
leftFrameColor = '#d0d0d0'
textColor = '#181825'
rightCONTENTFramecolor = 'grey'
rightCONTENTFrametxtcolor = 'white'

#Global Variables Declaration
songsdir,songname,filefound, = "","",""
global pausedornot, Mute, song_len, checksong, slide, pas, tl
checksong,slide,tl = "","",""
song_len = ""
pas = False
Mute = True
pausedornot = False
Stop = False

windows = tk.Tk()
windows.title('MusicByte - Music Player')

screen_width = windows.winfo_screenwidth()
screen_height = windows.winfo_screenheight()

x = int((screen_width/2) - (width/2))
y = int((screen_height/2) - (height/2))

windows.geometry("{}x{}+{}+{}".format(width, height, x, y))
windows.config(bg='#A9A9A9')
#root.resizable(False, False)
background = Label(windows, borderwidth=0)
background.place(x=0,y=0)

root=Frame(windows, height=height, width=width)
root.pack()
def window():   
    wintype = windows.state()
    if wintype == 'zoomed':
        temp = screen_height // 100
        temp = temp * 100
        var = temp - 620
        padding = var // 2
        root.pack(pady=padding)
        
    elif wintype == 'normal':
        root.config(highlightthickness=0)
        root.pack(pady=0)
    root.after(100, window)

mainWindowThread = threading.Thread(target=window)
mainWindowThread.start()

pygame.mixer.init()

def updatetitle(title):
    global tl
    tl = title
    title = title.replace('       ', '')
    global filefound
    if filefound != True:
        title = f'MusicByte - Add songs to playlist first! ' + title
        root.title(title)
        root.update()
        return
    title = f'MusicByte - Playing:   ' + title
    windows.title(title)
    windows.update()

def geticons(icons):
    base64_img_bytes = icons.encode('utf-8')
    decoded_image_data = base64.decodebytes(base64_img_bytes)
    ico = PhotoImage(data=decoded_image_data)
    return ico
def getsongINFO():
    global pas, slide
    if Stop:
        return
    activeClick = musiclist.get(ACTIVE)
    activeClick = activeClick.replace('       ', '')
    song = os.path.join(songsdir, activeClick)
    try:
            song_load = MP3(slide)
    except:
        return
    global song_len
    song_len = song_load.info.length
    

    def gettime():
        currentTIME = pygame.mixer.music.get_pos() / 1000
        ctyme = time.strftime('%M:%S', time.gmtime(currentTIME))
        styme = time.strftime('%M:%S', time.gmtime(song_len))
        #currentTIME+=1
        if int(progressBar1.get() == int(song_len)):
            progressBar.config(text=styme)
            foreward()
        elif pausedornot:
            pass
        elif int(progressBar1.get()) == int(currentTIME):
            #no movement to the slider
            sliderPOS = int(song_len)
            progressBar1.config(to=sliderPOS, value=int(currentTIME))
        else:
            #slider moved
            sliderPOS = int(song_len)
            progressBar1.config(to=sliderPOS, value=int(progressBar1.get()))
            ctyme = time.strftime('%M:%S', time.gmtime(int(progressBar1.get())))
            sliderlengthlbl.config(text=styme)
            progressBar.config(text=ctyme)
            nextt = int(progressBar1.get()) + 1
            progressBar1.config(value=nextt)
        #progressBar.config(text=f'Time Elapsed: {ctyme} of {styme}')
        #progressBar1.config(value=int(currentTIME)) #UPDATE SLIDER
        
        progressBar.after(1000, gettime)
    if pas == False:
        gettime()
        pas = True
    else:
        pass
    

def nextinfo(info):
    if info == None:
        artistlbl.config(text='Artist: N/A')
        lengthlbl.config(text=f'Length: N/A') 
        bitratelbl.config(text=f'Bitrate: N/A')
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
            artistlbl.config(text='Artist: Unknown Artist')
        else:
            artistlbl.config(text=f'Artist: {artist}')

        bitrate = song_load.info.bitrate / 1000

        lengthlbl.config(text=f'Length: {styme1}') 
        bitratelbl.config(text=f'Bitrate: {int(bitrate)}kbps')

def slider(x):
    global slide
    '''activeClick = musiclist.get(ACTIVE)
    activeClick = activeClick.replace('       ','')
    song = os.path.join(songsdir, activeClick)'''
    try:
        pygame.mixer.music.load(slide)
        pygame.mixer.music.play(loops=0, start=int(progressBar1.get()))
    except:
        pass
    #sliderLBL.config(text=f'{int(progressBar1.get())} of {int(song_len)}')

def volume(percent):
    pygame.mixer.music.set_volume(volumeSlider.get())
    vol = pygame.mixer.music.get_volume() * 100
    vLabelpercent.config(text=f'{int(vol)}%')

def mute(muteornot):
    global muteBTN, Mute
    if muteornot:
        pygame.mixer.music.set_volume(0)
        vLabelpercent.config(text='Muted')
        icon5 = geticons(MUTE)
        muteBTN.config(image=icon5)
        muteBTN.img = icon5
        Mute = False
    else:
        pygame.mixer.music.set_volume(volumeSlider.get())
        vol = pygame.mixer.music.get_volume() * 100
        vLabelpercent.config(text=f'{int(vol)}%')
        icon6 = geticons(UNMUTE)
        muteBTN.config(image=icon6)
        muteBTN.img = icon6
        Mute = True

def getmetadata(filee):
    global filefound
    tag = eye.Tag()
    try:
        tag.parse(filee)
        artist = tag.artist
        title = tag.title
        if artist == None:
            song_info1.config(text='Unknown Artist')
        else:
            song_info1.config(text=artist)
        if title == None:
            song_info.config(text='Unknown Title', font=('AdobeClean-Bold', 11))
        else:
            song_info.config(text=title, font=('AdobeClean-Bold', 11))
        filefound = True
    except:
        pass
    try:
        load = MP3(filee)
        songbit = load.info.bitrate // 1000
        songbitrate.config(text=f'Bitrate: {songbit}kbps')
    except:
        return

def getalbumArt(art, nextart):
    global filefound
    getmetadata(art)
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
        width = 230
        height = 230
        imggg = SM.open(path)
        try:
            left = 6
            top = screen_height / 2
            right = 900
            bottom = 2 * screen_height / 2
            im1 = imggg.crop((left, top, right, bottom)) 
            im2 = im1.resize((screen_width,screen_height), SM.ANTIALIAS)
            im2 = im2.filter(ImageFilter.GaussianBlur(radius=15)) 
            im2.save(BGPath)
            im2 = PhotoImage(file=BGPath)
            background.config(image=im2)
            background.img = im2
        except:
            pass
        imggg = imggg.resize((width,height), SM.ANTIALIAS)
        photoImg =  ImageTk.PhotoImage(imggg)
        for things in nowplayingIMG.winfo_children():
            things.destroy()
        nowplayingLabel = Label(nowplayingIMG, height=230, width=230, image=photoImg, borderwidth=0)
        nowplayingLabel.img = photoImg
        nowplayingLabel.place(x=0,y=0)
    except:
        for things in nowplayingIMG.winfo_children():
            things.destroy()
        imgg = geticons(NOImg)
        nowplayingLabel = Label(nowplayingIMG, height=230, width=230, image=imgg, borderwidth=0)
        nowplayingLabel.img = imgg
        nowplayingLabel.place(x=0,y=0)
    #For next album Art
    if nextart == None:
        for things in cunextpic.winfo_children():
                things.destroy()
        cunextpicLabel = Label(cunextpic, text="End Song Reached!", font=('AdobeClean-BOLD', 12), bg='#d0d0d0')
        cunextpicLabel.place(x=30,y=80)
    else:
        try:
            metadata=audio_metadata.load(nextart)
            artwork = metadata.pictures[0].data
            with open(path2, 'wb') as f:
                f.write(artwork)
            width = 200
            height = 200
            img = SM.open(path2)
            img = img.resize((width,height), SM.ANTIALIAS)
            photoImg1 =  ImageTk.PhotoImage(img)
            for things in cunextpic.winfo_children():
                things.destroy()
            cunextpicLabel = Label(cunextpic, height=200, width=200, image=photoImg1, borderwidth=0)
            cunextpicLabel.img = photoImg1
            cunextpicLabel.place(x=0,y=0)
        except:
            for things in nowplayingIMG.winfo_children():
                things.destroy()
            imgg1 = geticons(NOImg)
            cunextpicLabel = Label(cunextpic, height=200, width=200, image=imgg1, borderwidth=0)
            cunextpicLabel.img = imgg1
            cunextpicLabel.place(x=0,y=0)
    

def addlibFolder():
    global songsdir,musiclist,filefound
    songsdir = filedialog.askdirectory()
    try:
        songs = os.listdir(songsdir)
        filefound = True
    except FileNotFoundError:
        filefound = False
        return
    iconnn = geticons(PAUSE)
    playBTN.config(image=iconnn)
    playBTN.img = iconnn

    musiclist.delete('0', 'end')
    musiclist.config(yscrollcommand=scroll.set)
    scroll.config(command=musiclist.yview)
    musiclist.insert(ANCHOR, " \n ")
    for song in songs:
        musiclist.config(font=('AdobeClean-REGULAR', 10))
        musiclist.insert(END, f'       {song}')
    #musiclist.config(height=36, width=77)
    musiclist.config(height=25, width=77)
    
def addSongs():
    global songsdir, filefound, playBTN
    songFilename = filedialog.askopenfilenames(initialdir="/", title="Select File",
                                          filetypes=(("mp3 files", "*.mp3"),("all files", "*.*")))  
    if songFilename == "":
        filefound = False
        return
    else:
        filefound = True 
    iconnn = geticons(PAUSE)
    playBTN.config(image=iconnn)
    playBTN.img = iconnn                                 
    musiclist.delete('0', 'end')                                     
    musiclist.insert(ANCHOR, " \n ")                                      
    for song in songFilename:                                 
        songname = os.path.basename(song)
        musiclist.config(font=('AdobeClean-REGULAR', 10))
        musiclist.insert(END, f'       {songname}')
    musiclist.config(height=25, width=77)
    try:
        path = songFilename[0]
    except IndexError:
        return
    songname = os.path.basename(path)
    path = path.replace(songname, "")
    songsdir = path.replace("\\", "/")

def play(check):
    global Stop, checksong, tl, slide
    global pausedornot, playBTN
    Stop = False
    activeClick = musiclist.get(ACTIVE)
    updatetitle(activeClick)
    song = os.path.join(songsdir, activeClick)
    song = song.replace('\\', '/')
    song = song.replace('       ', '')

    upnext = musiclist.curselection()

    upnext = upnext[0]+1
    song2 = musiclist.get(upnext)
    filetype = song2[-3:]
    filetype = filetype.lower()
    if filetype == "mp3" or filetype == "wav" or filetype == "m4a" or filetype == "aac":
        path2 = os.path.join(songsdir, song2)
        path2 = path2.replace('\\', '/')
        path2 = path2.replace('       ', '')
    else:
        path2 = None

    nextinfo(path2)
    if song != checksong:
        try:
            pygame.mixer.music.load(song)
            pygame.mixer.music.play(loops=0)
            slide = song
            icon2 = geticons(PLAY)
            playBTN.config(image=icon2)
            playBTN.img = icon2
            checksong = song
            pausedornot = False
            #Reset Progress Slider
            progressBar1.config(value=0)
            getsongINFO()
            #sliderPOS = int(song_len)
            #progressBar1.config(to=sliderPOS, value=0)
        except:
            pass
    elif checksong == song:
        pausedornot = check
        if pausedornot:
            tl = tl.replace('       ', '')
            t = f'MusicByte - Playing:   ' + tl
            pygame.mixer.music.unpause()
            icon2 = geticons(PLAY)
            playBTN.config(image=icon2)
            playBTN.img = icon2
            windows.title(t)
            windows.update()
            pausedornot = False
        else:
            t = 'MusicByte - Paused'
            pygame.mixer.music.pause()
            iconnn = geticons(PAUSE)
            playBTN.config(image=iconnn)
            playBTN.img = iconnn
            windows.title(t)
            windows.update()
            pausedornot = True
    getalbumArt(song, path2)

def foreward():
    global playBTN, pausedornot, checksong, slide
    upnext = musiclist.curselection()
    iconnn = geticons(PLAY)
    playBTN.config(image=iconnn)
    playBTN.img = iconnn
    #Get the next song number (Tuple Number)
    nextsong = musiclist.curselection()
    try:
        nextsong = nextsong[0]+1
    except:
        return
    upnext = upnext[0]+2
    song2 = musiclist.get(upnext)
    filetype = song2[-3:]
    filetype = filetype.lower()
    if filetype == "mp3" or filetype == "wav" or filetype == "m4a" or filetype == "aac":
        path2 = os.path.join(songsdir, song2)
        path2 = path2.replace('\\', '/')
        path2 = path2.replace('       ', '')
    else:
        path2 = None

    song = musiclist.get(nextsong)
    if song == "" or song == None:
        return
    #Reset Progress Slider
    progressBar1.config(value=0)

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
        getsongINFO()
    except:
        pass
    try:
        musiclist.selection_clear(0, END)
        musiclist.activate(nextsong)
        musiclist.selection_set(nextsong, last=None)
        updatetitle(musiclist.get(ACTIVE))
    except:
        pass
    nextinfo(path2)
    getalbumArt(path, path2)
    
def previous():
    global playBTN, pausedornot, checksong, slide
    iconnn = geticons(PLAY)
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

    nextinfo(path2)
    path = os.path.join(songsdir, song)
    path = path.replace('\\', '/')
    path = path.replace('       ', '')


    try:
        #Reset Progress Slider
        progressBar1.config(value=0)

        pygame.mixer.music.load(path)
        pygame.mixer.music.play(loops=0)
        pausedornot = False
        checksong = path
        slide = path
        getsongINFO()
    except:
        pass

    try:
        musiclist.selection_clear(0, END)
        musiclist.activate(previoussong)
        musiclist.selection_set(previoussong, last=None)
        updatetitle(musiclist.get(ACTIVE))
    except:
        pass
    getalbumArt(path, path2)

def removeSongs(typee):
    global Stop
    currentsong = musiclist.curselection()
    #nextsong = currentsong[0]+1
    if typee == 'ONE':
        #Reset Progress Slider
        progressBar1.config(value=0)
        musiclist.delete(currentsong)
        pygame.mixer.music.stop()

        musiclist.selection_set(currentsong, last=None)
        nextsong = 0
        Stop = True
    elif typee == 'ALL':
        #Reset Progress Slider
        progressBar1.config(value=0)
        musiclist.delete(0, END)
        pygame.mixer.music.stop()
        Stop = True
    else:
        pass

def aboutwindow():
    width = 500
    height = 570
    win = tk.Toplevel()
    win.wm_title("MusicByte - About")
    screen_width = windows.winfo_screenwidth()
    screen_height = windows.winfo_screenheight()

    x = int((screen_width/2) - (width/2))
    y = int((screen_height/2) - (height/2))

    win.geometry("{}x{}+{}+{}".format(width, height, x, y))
    win.resizable(False, False)
    win.focus_set()
    mainico = geticons(MAIN)
    win.iconphoto(False, mainico)

    host = socket.gethostname()
    processor = platform.processor()
    System = f'{platform.system()}, {platform.version()}, {platform.architecture()[0]}'
    Machine = processor.split(',')

    infoframe = Frame(win, height=165, width=390)
    infoframe.place(x=45,y=15)
    lbl1 = Label(infoframe, text='MusicByte - Music Player', font=('AdobeClean-Bold', 13))
    lbl1.place(x=105,y=5)
    vlbl = Label(infoframe, text='Version 1.2.1')
    vlbl.place(x=160,y=30)
    line = Frame(win, height=1, width=397, highlightthickness=1, highlightbackground='black')
    line.place(x=49, y=80)
    lbl2 = Label(infoframe, text=f'Host Machine: {host}')
    lbl2.place(x=30, y=80)
    lbl3 = Label(infoframe, text=f'Current System: {System}')
    lbl3.place(x=30, y=100)
    lbl4 = Label(infoframe, text=f'Processor: {processor}')
    lbl4.place(x=30, y=120)
    lbl5 = Label(infoframe, text=f'Machine Type: {Machine[1]}')
    lbl5.place(x=30, y=140)

    line1 = Frame(win, height=1, width=397, highlightthickness=1, highlightbackground='black')
    line1.place(x=49, y=190)

    aboutframe = Frame(win, height=230, width=420)
    aboutframe.place(x=45, y=205)
    about = Label(aboutframe, text='MusicByte is a Stylish, Powerful and  Fast Music Player  with  elegant design. \n'\
                                    'It lets you manage all your music files and folder quickly and easily. \n\n'\
                                    'This audio  player  supports  almost all types of music files such as mp3, aac, \n' \
                                    'wav and m4a audio formats. Easily browse and play music songs by albums, \n'\
                                    'artists , songs and folder.', justify=LEFT)
    about.place(x=0,y=0)
    
    features = Label(aboutframe, text='Currently MusicByte fully Supports (Features): \n\n'\
                                        '    - A simple, flat and material UI design\n'\
                                        '    - Audio file formats such as MP3, WAV, M4A and AAC\n'\
                                        '    - Volume Slider and ProgressBar works fine\n'\
                                        '    - Add Songs via Folder or you can select single audio files\n'\
                                        '    - Remove songs, (current or all songs)', justify=LEFT)
    features.place(x=0, y=100)

    footer = Frame(win, height=60, width=420)
    footer.place(x=45,y=445)
    footerlbl = Label(footer, text='MusicByte player is a Music  Player  for  Windows. Send  me  the feedbacks,\n'\
                                    'bug-reports and suggestions about MusicByte to:', justify=LEFT)
    footerlbl.place(x=0,y=0)
    emaillbl = Label(footer, text='imshawan.dev049@gmail.com',fg="blue", cursor="hand2")
    emaillbl.place(x=110,y=35)

    b = ttk.Button(win, text="Close", command=win.destroy)
    b.place(x=210, y=520)

def licenses():
    width = 500
    height = 480
    win = tk.Toplevel()
    win.wm_title("MusicByte - View Licenses")
    screen_width = windows.winfo_screenwidth()
    screen_height = windows.winfo_screenheight()

    x = int((screen_width/2) - (width/2))
    y = int((screen_height/2) - (height/2))

    win.geometry("{}x{}+{}+{}".format(width, height, x, y))
    win.resizable(False, False)
    win.focus_set()
    mainico = geticons(MAIN)
    win.iconphoto(False, mainico)
    infoframe = Frame(win, height=60, width=390)
    infoframe.place(x=45,y=5)
    lbl1 = Label(infoframe, text='MusicByte - Music Player', font=('AdobeClean-Bold', 13))
    lbl1.place(x=105,y=5)
    vlbl = Label(infoframe, text='Version 1.2.1')
    vlbl.place(x=160,y=30)
    mit = Label(win, text='MIT License')
    mit.place(x=208,y=80)
    copyryt = Label(win, text='Copyright (c) 2020 Shawan Mandal')
    copyryt.place(x=150,y=105)

    bottomfrm = Frame(win, height=290, width=420)
    bottomfrm.place(x=45, y=130)
    textlbl = Label(bottomfrm, text='Permission is hereby granted, free of charge, to any person obtaining a copy\n'\
                                    'of this software and associated documentation files (the "Software"), to deal\n'\
                                    'in the Software without restriction, including without limitation the rights to\n'\
                                    'use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies\n'\
                                    'of the Software, and to permit persons to whom the Software is furnished to \n'\
                                    'do so, subject to the following conditions:\n\n'\
                                    'The above copyright notice and this permission  notice shall be included in\n'\
                                    'all copies or substantial portions of the Software.\n\n'\
                                    'THE  SOFTWARE  IS  PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,\n'\
                                    'EXPRESS  OR  IMPLIED, INCLUDING  BUT NOT LIMITED TO THE WARRANTIES \n'\
                                    'OF MERCHANTABILITY, FITNESS  FOR  A  PARTICULAR PURPOSE AND NON-\n'\
                                    'INFRINGEMENT.IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLD-\n'\
                                    'ERS BE  LIABLE  FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER\n'\
                                    'IN AN ACTION  OF CONTRACT, TORT  OR OTHERWISE, ARISING FROM, OUT\n'\
                                    'OF  OR  IN  CONNECTION  WITH  THE  SOFTWARE  OR  THE  USE  OR OTHER\n'\
                                    'DEALINGS IN THE SOFTWARE.', justify=LEFT)
    textlbl.place(x=0,y=0)

    b = ttk.Button(win, text="Close", command=win.destroy)
    b.place(x=205, y=420)

#END OF ALL FUNCTIONS

#---------------------------------------------------Actual Designing Starts here---------------------------------------------------

#APPLICATION MAIN ICON
mainico = geticons(MAIN)
windows.iconphoto(False, mainico)

#RIGHT FRAME, MUSIC LIST
rightFrame = Frame(root,height=600, width=620, bg='#fafafa')
rightFrame.place(x=250, y=20)

#RIGHTCONTENT FRAME, AFTER MUSIC LIST 
imageee = geticons(RIGHT_FRAME)
rightCONTENTFrame = Frame(root, height=620, width=250,bg=rightCONTENTFramecolor)
rightCONTENTFrame.place(x=810, y=0)
sha = Label(rightCONTENTFrame, height=620, width=250, image=imageee, borderwidth=0)
sha.place(x=0,y=0)

cunext = Frame(rightCONTENTFrame, height=30, width=200,bg='#0f51c9')
cunext.place(x=23, y=10)
cunextlbl = Label(cunext, text='Comming Up next',fg='white', bg='#0f51c9',font=('AdobeClean-Bold', 13))
cunextlbl.place(x=25,y=0)
cunextpic = Frame(rightCONTENTFrame, height=200, width=200, bg='#d0d0d0')
cunextpic.place(x=23,y=40)

detailsframe = Frame(rightCONTENTFrame, height=70, width=225, bg=rightCONTENTFramecolor)
detailsframe.place(x=10, y=245)
artistlbl = Label(detailsframe, text='Artist: ',bg=rightCONTENTFramecolor, fg=rightCONTENTFrametxtcolor)
artistlbl.place(x=0, y=5)
lengthlbl = Label(detailsframe, text='Length: ',bg=rightCONTENTFramecolor, fg=rightCONTENTFrametxtcolor)
lengthlbl.place(x=0, y=25)
bitratelbl = Label(detailsframe, text='Bitrate: ',bg=rightCONTENTFramecolor, fg=rightCONTENTFrametxtcolor)
bitratelbl.place(x=0, y=45)

#MUSIC LIST DISPLAY BOX
musicboxFRAME = Frame(root,height=500, width=560)
musicboxFRAME.place(x=250,y=20)
musiclist = Listbox(musicboxFRAME, height=27, width=90, borderwidth=0, bg='#f0f0f0')
musiclist.pack(side='left', fill='y')
scroll = Scrollbar(musicboxFRAME, orient='vertical')
scroll.pack(side='right', fill='y')

#LEFT FRAME-----------------------------------------------------------------------------------
leftFrame = Frame(root, height=620, width=250, bg=leftFrameColor)#bg='#eeeeee'
leftFrame.place(x=0,y=0)
lftImg = geticons(LEFT_FRAME)
lftframe = Label(leftFrame, height=700, width=250, image=lftImg, borderwidth=0)
lftframe.place(x=0, y=0)

#HEADING (PLAYER NAME)
head = Frame(leftFrame, height=50, width=173,bg=leftFrameColor)
head.place(x=35,y=15)
pic = geticons(MUSICBYTE)
headlbl = Label(head, image=pic, bg=leftFrameColor) #font=('CoolveticaRg-Regular', 25) text='MusicByte',
headlbl.place(x=0,y=5)

#MANAGEMENT i.e ADD SONGS AND ETC OPTIONS
addlibrary = Frame(leftFrame, height=280, width=210, bg=leftFrameColor)
addlibrary.place(x=10, y=70)
text1 = Label(addlibrary, text="LIBRARY",font=('AdobeClean-Bold', 13), fg=textColor,bg=leftFrameColor) #HEADING: LIBRARY fg='#686868'
text1.place(x=10,y=5)
text2 = Label(addlibrary, text="Music",font=('AdobeClean-REGULAR', 13), fg=textColor,bg=leftFrameColor) #SUBHEADINGS
text2.place(x=55,y=40)
musicico = geticons(MUSIC)
musiclabel = Label(addlibrary, image=musicico, bg=leftFrameColor)
musiclabel.place(x=28,y=43)
btn = Button(addlibrary, text="Add library",font=('AdobeClean-REGULAR', 12), borderwidth=0, fg=textColor,bg=leftFrameColor, command=addlibFolder) #ADD FOLDER TO LIBRARY
btn.place(x=55,y=70)
btn1 = Button(addlibrary, text="Add Songs",font=('AdobeClean-REGULAR', 12), borderwidth=0, fg=textColor,bg=leftFrameColor, command=addSongs) #ADD SONGS TO LIBRARY
btn1.place(x=55,y=95)
btn2 = Button(addlibrary, text="Remove current song",font=('AdobeClean-REGULAR', 12), borderwidth=0, fg=textColor,bg=leftFrameColor, command=lambda: removeSongs('ONE')) #Removes current song from LIBRARY
btn2.place(x=55,y=120)
btn3 = Button(addlibrary, text="Remove all Songs",font=('AdobeClean-REGULAR', 12), borderwidth=0, fg=textColor,bg=leftFrameColor, command=lambda: removeSongs('ALL')) #Removes all songs from LIBRARY
btn3.place(x=55,y=145)
text3 = Label(addlibrary, text="USER CONTROL",font=('AdobeClean-Bold', 13), fg=textColor,bg=leftFrameColor) #HEADING: DETAILS
text3.place(x=10,y=180)
aboutbtn = Button(addlibrary, text="About", font=('AdobeClean-REGULAR', 12), borderwidth=0, fg=textColor,bg=leftFrameColor, command=aboutwindow)
aboutbtn.place(x=55, y=210)
licensebtn = Button(addlibrary, text='View License', font=('AdobeClean-REGULAR', 12), borderwidth=0, fg=textColor,bg=leftFrameColor, command=licenses)
licensebtn.place(x=55, y=235)



#NOW PLAYING
nowplaying = Frame(leftFrame, height=260, width=230)
nowplaying.place(x=10,y=350)
nowtext = Frame(nowplaying,height=30,width=230,bg='#0f51c9')
nowtext.place(x=0,y=0)
nowlabel = Label(nowtext, text="Now Playing",bg='#0f51c9',fg='white',font=('AdobeClean-Bold', 13))
nowlabel.place(x=50,y=0)
nowplayingIMG = Frame(nowplaying, height=230, width=230, bg='gray')
nowplayingIMG.place(x=0, y=30)

#CONTROL FRAME (MAIN)-------------------------------------------------------------------------
controlFRAME = Frame(root,height=100, width=560)
controlFRAME.place(x=250,y=520)

#Time FUNCTION
sliderlength = Frame(controlFRAME, height=21, width=35)
sliderlength.place(x=500, y=5)
sliderlengthlbl = Label(sliderlength, text='00:00')
sliderlengthlbl.place(x=0,y=0)
timeframe = Frame(controlFRAME, height=21, width=40)
timeframe.place(x=20, y=7)
progressBar = Label(timeframe, text="00:00", relief=GROOVE, anchor=E, borderwidth=0)
progressBar.pack(fill=X, side=BOTTOM)


#SLIDER FRAME
sliderFrame = Frame(controlFRAME, height=21, width=350)
sliderFrame.place(x=58, y=4)
progressBar1 = ttk.Scale(sliderFrame, from_=0, to=100, orient=HORIZONTAL, value=0,length=432, command=slider)
progressBar1.pack()


#CONTROLS
controlFrame1 = Frame(controlFRAME, height=48, width=140)
controlFrame1.place(x=200,y=33)

icon1 = geticons(PLAY)
global playBTN
playBTN = Button(controlFrame1, image=icon1, borderwidth=0, command=lambda: play(pausedornot))
icon3 = geticons(FOREWARD)
forewardBTN = Button(controlFrame1, image=icon3, borderwidth=0, command=foreward)
icon4 = geticons(BACK)
backBTN = Button(controlFrame1, image=icon4, borderwidth=0, command=previous)
icon5 = geticons(MUTE)

backBTN.place(x=0,y=15)
playBTN.place(x=45,y=0)
forewardBTN.place(x=104,y=15)

#NOW PLAYING SONG INFO------------------------------------------------------------------------
songInfoframe = Frame(root, height=80, width=560)
songInfoframe.place(x=250, y=448)
songInfofr = Frame(songInfoframe, height=50, width=470)
songInfofr.place(x=20, y=8)
songInfofr1 = Frame(songInfoframe, height=50, width=470)
songInfofr1.place(x=20, y=30)
songInfofrbit = Frame(songInfoframe, height=20, width=200)
songInfofrbit.place(x=20, y=48)

song_info = Label(songInfofr, text="Unknown Song")
song_info.config(font=('AdobeClean-Bold', 11))
song_info.pack()
song_info1 = Label(songInfofr1, text="Unknown Artist")
song_info1.pack()
songbitrate = Label(songInfofrbit, text="Bitrate: ")
songbitrate.pack()

#VOLUME CONTROLS------------------------------------------------------------------------------
volFrame = Frame(controlFRAME, height=30, width=30)#bg=leftFrameColor)
volFrame.place(x=20,y=42)

global muteBTN
icon6 = geticons(UNMUTE)
muteBTN = Button(volFrame, image=icon6, borderwidth=0, command=lambda: mute(Mute))
muteBTN.place(x=2,y=5)

#VOLUME PERCENTAGE
volpercentFrame = Frame(controlFRAME, height=20, width=100)
volpercentFrame.place(x=60,y=46)
vLabel = Label(volpercentFrame, text='Volume:',fg=textColor)
vLabel.place(x=0, y=0)
vLabelpercent = Label(volpercentFrame, text='75%', fg=textColor)
vLabelpercent.place(x=50, y=0)


#VOLUME SLIDER
volsliderFrame = Frame(controlFRAME, height=21, width=250, bg=leftFrameColor)
volsliderFrame.place(x=375, y=45)
volumeSlider = ttk.Scale(volsliderFrame, from_=0, to=1, orient=HORIZONTAL, value=0.75,length=158, command=volume)
volumeSlider.pack()

windows.mainloop()
