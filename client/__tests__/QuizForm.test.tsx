import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import QuizForm from '@features/quiz/components/QuizForm';

const mockPush = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

jest.mock('@features/auth/context/authContext', () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
  }),
}));

jest.mock('@shared/api/http', () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

describe('QuizForm', () => {
  beforeEach(() => {
    mockPush.mockClear();
  });

  test('renders the quiz form with initial state', () => {
    render(<QuizForm />);

    expect(screen.getByPlaceholderText('Enter the concept/context here')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /generate quiz/i })).toBeInTheDocument();
  });

  test('updates question input on change', () => {
    render(<QuizForm />);

    const input = screen.getByPlaceholderText('Enter the concept/context here');
    fireEvent.change(input, { target: { value: 'What is your favorite color?' } });

    expect(input).toHaveValue('What is your favorite color?');
  });

  test('generates quiz and redirects to quiz display', async () => {
    render(<QuizForm />);

    const input = screen.getByPlaceholderText('Enter the concept/context here');
    fireEvent.change(input, { target: { value: 'What is your favorite color?' } });

    const generateButton = screen.getByRole('button', { name: /generate quiz/i });
    fireEvent.click(generateButton);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith(
        expect.stringContaining('/quiz_display?'),
      );
    });
  });
});
