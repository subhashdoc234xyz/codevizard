def main():
    numbers = []
    for i in range(10):
        while True:
            try:
                num = int(input(f"Enter integer #{i + 1}: "))
                numbers.append(num)
                break
            except ValueError:
                print("Invalid input. Please enter an integer.")
    print("\nYou entered:")
    for num in numbers:
        print(num)

if __name__ == "__main__":
    main()