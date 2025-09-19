import argparse
import os
import subprocess
import sys

from perception import hashers

image_exts = [
	"bmp", "jpg", "jpeg", "png", "tif", "tiff", "webp",
	"jp2", "j2k", "jpf", "jpm", "jpg2", "j2c", "jpc", "jpx"
	]

# Pair of potential duplicates and the distance between them.
class Pair:
    def __init__(self, file1, file2, dist):
        self.file1 = file1
        self.file2 = file2
        self.dist = dist

    def __format__(self):
        return "{}\t{}\t{}".format(self.file1, self.file2, self.dist)

def print_pairs(pairs):
    for p in pairs:
        print(p)

# Identify pairs of potential duplicates based on the parameters set by the user.
def find_dups(files, args):
    hasher = hashers.PHash(hash_size=16)

    # Compute hashes but leave a hash of None if it could not be calculated.
    hashes = []
    for file in files:
        try:
            hashes.append(hasher.compute(file))
        except:
            if not args.quiet:
                print("failed to compute hash for {}".format(file), file=sys.stderr)
                hashes.append(None)

    # Calculate distance between all pairs of hashes and save those under the
    # threshold, then sort those by ascending distance (so closest are first).
    pairs = []
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            if hashes[i] is None or hashes[j] is None:
                continue
            distance = hasher.compute_distance(hashes[i], hashes[j])
            if distance <= args.threshold:
                pairs.append(Pair(files[i], files[j], distance))
    pairs.sort(key = lambda p: p.dist)

    return pairs

# Show images to the user and return the ones they select by index.
def choose_with_viewer(dups, cmd):
    chosen = []
    cmd = cmd.split() + dups
    try:
        proc = subprocess.Popen(cmd + dups, stdin=subprocess.PIPE)
    except:
        # Ask whether or not to continue ()
        print("failed to run command: {}".format(' '.join(cmd)), file=sys.stderr)

    # Ask user for which files to save by index.
    receiving_input = True
    while receiving_input:
        chosen = []
        save = input("Images to save? [default=1, a for all, c for cancel] ")
        receiving_input = False
        if save.strip().lower().startswith("a"):
            chosen = dups
        elif save.strip().lower().startswith("c"):
            print("could not complete deduplication", file=sys.stderr)
            sys.exit(1)
        elif len(save) <= 0 or save.isspace():
            chosen.append(dups[0])
        else:
            for f in save.split(","):
                n = f.strip()
                if n.isdigit():
                    chosen.append(dups[int(n) - 1])
                else:
                    # Input was not well formed.
                    receiving_input = True

    # Terminate image viewer.
    if proc is not None:
        proc.terminate()

    return chosen

# Identify duplicates to delete based on the paramaters set by the user.
def identify_to_delete(pairs, args):
    # Iterate through pairs of duplicates, display duplicates in feh, and allow
    # the user to choose which to save.
    i = 0
    to_delete = []
    while i < len(pairs):
        # Check if the auto-deletion threshold is met.
        while args.auto_threshold is not None and i < len(pairs) and pairs[i].dist <= args.auto_threshold:
            to_delete.append(pairs[i].file2)
            i += 1
        # Make sure the file is not already scheduled for deletion.
        while i < len(pairs) and pairs[i].file1 in to_delete:
            i += 1
        # Exit the loop if we have gone past the end.
        if i >= len(pairs):
            break

        dups = [pairs[i].file1]
        # Keep iterating through until we get a pair starting with a different
        # file, in order to collect all duplicates of this file.
        while i < len(pairs) and pairs[i].file1 == dups[0]:
            if pairs[i].file2 not in to_delete:
                dups.append(pairs[i].file2)
            i += 1
        # Make sure that we are left with more than one image to show.
        if len(dups) <= 1:
            i += 1
            continue

        # If the -a option is on, automatically delete all duplicates.
        if args.auto_threshold is not None:
            to_delete.extend(dups[1:])
        # Otherwise let the user choose what to save.
        else:
            # Mark all files not selected with feh for deletion.
            to_save = choose_with_viewer(dups, args.viewer_command)
            to_delete.extend([d for d in dups if d not in to_save])

    return to_delete

# Delete the files provided, or print them without deleting if `dry_run` is True.
def delete_files(files, dry_run=False):
    for d in files:
        if dry_run:
            print(d)
        else:
            try:
                os.remove(d)
            except:
                print("could not delete {}".format(d), file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(
        prog="Image Duplicate Finder"
    )
    parser.add_argument("images", nargs="+")
    parser.add_argument("-l", "--list", default=False, action="store_true",
                        help="print list of pairs of duplicates sorted by distance instead of deleting")
    parser.add_argument("-c", "--viewer-command", default="feh -.", type=str,
                        help="command used to show potential duplicates (default feh -.)")
    parser.add_argument("-t", "--threshold", default=0.3, type=float, metavar="T",
                        help="the threshold at which to show potential duplicates for manual checking (default 0.3), or,"
                        "if used with the -l flag, the threshold at which to include potential duplicates in the output")
    parser.add_argument("-a", "--auto-threshold", default=None, type=float, metavar="A",
                        help="the threshold at which to automatically delete potential duplicates (default none)")
    parser.add_argument("-f", "--force", default=False, action="store_true",
                        help="disable file extension check before operating on files")
    parser.add_argument("-q", "--quiet", default=False, action="store_true")
    parser.add_argument("-d", "--dry-run", default=False, action="store_true",
                        help="print list of files to delete instead of actually deleting")

    args = parser.parse_args()

    # Get a list of images supplied by command-line arguments, as well as images
    # in supplied folders.
    files = []
    for i in args.images:
        if os.path.isfile(i):
            files.append((i, os.path.getmtime(i)))
        elif os.path.isdir(i):
            for r, d, f in os.walk(i):
                for name in f:
                    fp = os.path.join(r, name)
                    if name.split(".")[-1].lower() in image_exts or args.force:
                        files.append(fp)
                    elif not args.quiet:
                        print("{} is not a compatible image format, skipping...".format(fp), file=sys.stderr)
        else:
            print("could not find {}".format(i), file=sys.stderr)
            sys.exit(1)

    # Sort by last modification time so that older files are preferred.
    files.sort(key=lambda f: os.path.getmtime(f))

    pairs = find_dups(files, args)

    if args.list:
        print_pairs(pairs)
    else:
        to_delete = identify_to_delete(pairs, args)
        delete_files(to_delete, args.dry_run)

if __name__ == "__main__":
    main()
