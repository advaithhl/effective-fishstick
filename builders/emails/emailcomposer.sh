#!/bin/bash

# Check if five command-line arguments are provided
if [ $# -ne 4 ]; then
  echo "Required command line arguments not provided."
  exit 1
fi

# Assign command-line arguments to variables
EMAIL_VAR1="$1"
EMAIL_VAR2="$2"
EMAIL_VAR3="$3"
EMAIL_VAR4="$4"

# Input HTML file
input_file="tfcplanoutput_template.html"

# Output HTML file
output_file="tfcplanoutput.html"

# Use sed to replace variables in the HTML file
sed "s~EMAIL_VAR1~$EMAIL_VAR1~g; s~EMAIL_VAR2~$EMAIL_VAR2~g; s~EMAIL_VAR3~$EMAIL_VAR3~g; s~EMAIL_VAR4~$EMAIL_VAR4~g" "$input_file" > "$output_file"

echo "Mail composed and saved as '$output_file'."
