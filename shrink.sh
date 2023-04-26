
if [ "$#" -ne 2 ]; then
    echo "Usage: shrink <filename> <number_of_lines>"
    exit 1
fi

filename="$1"
n_lines="$2"

if ! [[ "$n_lines" =~ ^[0-9]+$ ]]; then
    echo "Error: Second argument must be a positive integer."
    exit 1
fi

if [ ! -f "$filename" ]; then
    echo "Error: File not found."
    exit 1
fi

total_lines=$(wc -l < "$filename")
start_line=$((total_lines - n_lines + 1))

if [ "$start_line" -le 0 ]; then
    echo "Error: Number of lines requested is greater than the total lines in the file."
    exit 1
fi

sed -i "1,$((start_line - 1))d" "$filename"
