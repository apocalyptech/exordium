This is nearly an exact copy of the default "pink.flag" skin from jPlayer.
The only actual difference is that image/jplayer.pink.flag.jpg has been
updated to be much wider, to accomodate the resolution I'm interested in.
The CSS hasn't been updated at all because I don't care to figure out how
to re-minify it after editing the master, so all necessary CSS tweaks are
being done in the page which includes this.

For reference, these are the tweaks necessary to make everything look all
right:

    .jp-audio {
        width: 558px;
    }
    .jp-volume-bar {
        width: 554px;
    }
    .jp-progress {
        width: 554px;
    }

Pretty simple!
