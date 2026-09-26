from invoice import line_total_cents

# Test cases
print('test_full_price:', line_total_cents(199, 3, 0) == 597)
print('test_half_cent_rounds_up:', line_total_cents(25, 1, 50) == 13)
print('test_tiny_line_still_rounds_up:', line_total_cents(5, 1, 90) == 1)

# Test ValueError
try:
    line_total_cents(100, 1, 101)
    print('test_discount_out_of_range: False')
except ValueError:
    print('test_discount_out_of_range: True')
