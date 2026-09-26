from invoice import line_total_cents

# Test 1: full price
result1 = line_total_cents(199, 3, 0)
print(f'test_full_price: {result1} == 597? {result1 == 597}')

# Test 2: half cent rounds up
result2 = line_total_cents(25, 1, 50)
print(f'test_half_cent_rounds_up: {result2} == 13? {result2 == 13}')

# Test 3: tiny line still rounds up
result3 = line_total_cents(5, 1, 90)
print(f'test_tiny_line_still_rounds_up: {result3} == 1? {result3 == 1}')

# Test 4: discount out of range
try:
    line_total_cents(100, 1, 101)
    print('test_discount_out_of_range: FAILED (no exception)')
except ValueError:
    print('test_discount_out_of_range: PASSED (ValueError raised)')
