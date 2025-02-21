import numpy as np

# Define ETF information
etfs = ["VGT", "QQQM", "SCHD", "JEPI", "JEPQ"]
targets = [1000, 1000, 1000, 2500, 2500]
prices = [625, 216, 28, 59, 57]
total_budget = 8000

# Function to calculate allocation metrics
def calculate_allocation_metrics(shares):
    actual_investments = [shares[i] * prices[i] for i in range(len(etfs))]
    total_invested = sum(actual_investments)
    remainder = total_budget - total_invested
    
    # Calculate target percentages and actual percentages
    target_percentages = [t/sum(targets)*100 for t in targets]
    actual_percentages = [a/total_invested*100 for a in actual_investments]
    
    # Calculate deviation from target percentages
    percentage_deviations = [abs(actual_percentages[i] - target_percentages[i]) for i in range(len(etfs))]
    total_deviation = sum(percentage_deviations)
    
    return actual_investments, total_invested, remainder, actual_percentages, total_deviation

# Initial allocation (floor division)
initial_shares = [int(targets[i] / prices[i]) for i in range(len(etfs))]
initial_metrics = calculate_allocation_metrics(initial_shares)

# Optimization approach: Add shares one by one to minimize remainder
current_shares = initial_shares.copy()
current_metrics = initial_metrics

# Keep adding shares until we can't add more without exceeding budget
while True:
    best_deviation = float('inf')
    best_idx = -1
    best_metrics = None
    
    # Try adding one share to each ETF and see which gives best result
    for i in range(len(etfs)):
        test_shares = current_shares.copy()
        test_shares[i] += 1
        test_metrics = calculate_allocation_metrics(test_shares)
        
        # Check if this allocation is within budget and improves deviation
        if test_metrics[2] >= 0 and test_metrics[4] < best_deviation:
            best_deviation = test_metrics[4]
            best_idx = i
            best_metrics = test_metrics
    
    # If no improvement found, break
    if best_idx == -1:
        break
    
    # Update current shares and metrics
    current_shares[best_idx] += 1
    current_metrics = best_metrics

# Display results
print(f"Total Budget: ${total_budget}")
print("\nOptimized Allocation:")
print(f"{'ETF':<6} {'Target($)':<10} {'Price($)':<10} {'Shares':<8} {'Actual($)':<12} {'Target%':<10} {'Actual%':<10}")
print("-" * 70)

actual_investments = current_metrics[0]
total_invested = current_metrics[1]
remainder = current_metrics[2]
actual_percentages = current_metrics[3]
target_percentages = [t/sum(targets)*100 for t in targets]

for i in range(len(etfs)):
    print(f"{etfs[i]:<6} ${targets[i]:<9} ${prices[i]:<9} {current_shares[i]:<8} ${actual_investments[i]:<11.2f} {target_percentages[i]:<9.2f}% {actual_percentages[i]:<9.2f}%")

print("-" * 70)
print(f"Total Invested: ${total_invested:.2f}")
print(f"Remainder: ${remainder:.2f}")
