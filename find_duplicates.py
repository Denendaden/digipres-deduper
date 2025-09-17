import argparse
import os
import subprocess
import sys

from perception import hashers

image_exts = ["jpg", "jpeg", "png", "tif", "tiff"]

def main():
    parser = argparse.ArgumentParser(
        prog="Image Duplicate Finder"
    )
    parser.add_argument("images", nargs="+")
    parser.add_argument("-t", "--threshold", default=0.3, type=float)
    parser.add_argument("-q", "--quiet", default=False, action="store_true")
    parser.add_argument("-a", "--auto-threshold", default=0.05, type=float)
    parser.add_argument("-A", "--automatic", default=False, action="store_true")
    parser.add_argument("-m", "--manual", default=False, action="store_true")

    args = parser.parse_args()

    hasher = hashers.PHash(hash_size=16)

    # Get a list of images supplied by command-line arguments, as well as images
    # in supplied folders.
    files = []
    for i in args.images:
        if os.path.isfile(i):
            if i.split(".")[-1].lower() in image_exts:
                files.append((i, os.path.getmtime(i)))
            elif not args.quiet:
                print("{} is not a compatible image, skipping...".format(i), file=sys.stderr)
        elif os.path.isdir(i):
            for r, d, f in os.walk(i):
                for name in f:
                    fp = os.path.join(r, name)
                    if name.split(".")[-1].lower() in image_exts:
                        files.append((fp, os.path.getmtime(fp)))
                    elif not args.quiet:
                        print("{} is not a compatible image, skipping...".format(fp), file=sys.stderr)
        else:
            print("could not find {}".format(i), file=sys.stderr)
            sys.exit(1)

    # Sort by last modification time so that older files are preferred.
    files.sort(key=lambda f: f[1])

    # Compute hashes but leave a hash of None if it could not be calculated.
    hashes = []
    for file in files:
        try:
            hashes.append(hasher.compute(file[0]))
        except:
            if not args.quiet:
                print("failed to compute hash for {}".format(file[0]), file=sys.stderr)
                hashes.append(None)

    # Calculate distance between all pairs of hashes and save those under the
    # threshold, then sort those by ascending distance (so closest are first).
    pairs = []
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            if hashes[i] is None or hashes[j] is None:
                continue
            distance = hasher.compute_distance(hashes[i], hashes[j])
            if distance < args.threshold:
                pairs.append((files[i][0], files[j][0], distance))
    pairs.sort(key = lambda p: p[2])

    # Iterate through pairs of duplicates, display duplicates in feh, and allow
    # the user to choose which to save.
    i = 0
    to_delete = []
    while i < len(pairs):
        # Check if the auto-deletion threshold is met.
        while i < len(pairs) and pairs[i][2] <= args.auto_threshold and not args.manual:
            to_delete.append(pairs[i][1])
            i += 1
        # Make sure the file is not already scheduled for deletion.
        while i < len(pairs) and pairs[i][0] in to_delete:
            i += 1
        # Exit the loop if we have gone past the end.
        if i >= len(pairs):
            break

        dups = [pairs[i][0]]
        # Keep iterating through until we get a pair starting with a different
        # file, in order to collect all duplicates of this file.
        while i < len(pairs) and pairs[i][0] == dups[0]:
            if pairs[i][1] not in to_delete:
                dups.append(pairs[i][1])
            i += 1
        # Make sure that we are left with more than one image to show.
        if len(dups) <= 1:
            i += 1
            continue

        # If the -A option is on, automatically delete all duplicates.
        if args.automatic:
            to_delete.extend(dups[1:])
        # Otherwise let the user choose what to save.
        else:
            # Show the duplictes in feh.
            try:
                proc = subprocess.Popen(["feh", "-."] + dups, stdin=subprocess.PIPE)
                receiving_input = True
                to_save = []
                while receiving_input:
                    to_save = []
                    save = input("Images to save? [default=1] ")
                    receiving_input = False
                    if save.strip().lower().startswith("a"):
                        to_save = dups
                    elif len(save) <= 0 or save.isspace():
                        to_save.append(dups[0])
                    else:
                        for f in save.split(","):
                            n = f.strip()
                            if n.isdigit():
                                to_save.append(dups[int(n) - 1])
                            else:
                                # Input was not well formed.
                                receiving_input = True
                to_delete.extend([d for d in dups if d not in to_save])
                proc.terminate()
            except:
                print("could not start feh (is it installed?)", file=sys.stderr)
                sys.exit(1)

    # Delete files.
    for d in to_delete:
        try:
            os.remove(d)
        except:
            print("could not delete {}".format(d), file=sys.stderr)

if __name__ == "__main__":
    main()
