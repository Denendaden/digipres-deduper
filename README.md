# Digital Preservation Image Deduplicater

This is a tool for deduplicating collections of images, using the Python [Perception](https://pypi.org/project/Perception/) library.

## Usage

```
$ python dedup.py TARGET...
```

This command, by default, will display all sets of potential duplicates (distance <= 0.3) in the (by default) `feh` image viewer and allow the user to select which to preserve from each set.
`TARGET` is a list of files and directories; the program will recursively search all directories passed and operate on all files inside.

Keep in mind that the perceptual hashing algorithm is not designed for images of text, and will tend to recognize images of different paragraphs of text as duplicates.

The threshold used by the program can be customized with the `t` or `--threshold` option:

```
$ python dedup.py -t 0.2 TARGET...
```

The `-a` (`--auto-threshold`) option is provided to streamline this by setting a distance threshold below which the program will automatically delete the duplicates it detects, preserving the oldest file:

```
$ python dedup.py -a 0.1 TARGET...
```

If no manual checking is desired, `-a` can be set to a value higher than `-t`:

```
$ python dedup.py -t 0 -a 0.2 TARGET...
```

### Options

- `-l`/`--list`: output a list (to stdout) of pairs of potential duplicates sorted by distance instead of deleting.
- `-c`/`--viewer-command`: command to use to view potential duplicates while selecting which to save. (default="feh -.")
- `-t`/`--threshold`: the threshold used to identify potential duplicates to show the user, or if `-l` is enabled, the threshold at which to include potential duplicate pairs in the output. (default=0.3)
A value of 0.2 is unlikely to provide false positives.
Images with a distance > 0.5 are often entirely different from each other.
- `-a`/`--auto-threshold`: the threshold at which potential duplicates will be automatically deleted, with the oldest file being preserved.
By default, this functionality is disabled; the option `-a 0` will cause the program to automatically delete exact duplicates.
- `-f`/`--force`: disables the file extension check and attempts to hash all files passed.
- `-q`/`--quiet`: silences non-fatal errors and warnings, such as when a hash could not be calculated for a file.
- `-d`/`--dry-run`: output a list of files to delete instead of deleting.

## Compatible file types

The program has been tested on and works with at least some JPEG, PNG, BMP, TIFF, WEBP, and JP2 files.
We have confirmed it does not work on GIF, PDF, SVG, AVIF, or HEIC files.
These lists may not be exhaustive.

The program identifies file types by extension and, for the sake of efficiency, will not attempt to hash files with different extensions than those listed above when recursively searching a directory,
If it is desireable to disable this check (such as if you have files with mismatched/nonstandard extensions or rare filetypes you want to check), these files can be individually specified on the command line or the `-f` option can be used to disable the check and force the program to try to hash every file.
