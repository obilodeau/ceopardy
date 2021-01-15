#!/usr/bin/env perl
#
# pass me a round file and i'll give you the questions
#
# meant to be run with cat $roundfile | perl -n extract-board.pl

use strict;
use warnings;

use feature 'say';

chomp;

if (/^final:/) {
    say $_;
    next;
}
# categories
else {
    say `grep -P -A 12 "^>$_" Jeopardy`;
}
